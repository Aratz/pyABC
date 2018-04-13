from typing import List, Callable
import pandas
from pyabc.parameters import Parameter


class Particle:
    """
    An (accepted or rejected) particle, containing the information that will
    also be stored in the database.
    Stores all summary statistics that
    were generated during the creation of this particle, and a flag
    indicating whether this particle was accepted or not.

    Properties
    ----------

    m: int
        The model nr

    parameter: Parameter
        The model specific parameter

    weight: float, 0 < weight < 1
        The weight of the particle

    distances: List[float]
        A particle can contain more than one sample.
        If so, the distances of the individual samples
        are stored in this list. In the most common case of a single
        sample, this list has length 1.

    accepted_sum_stats
        List of accepted summary statistics which describe the particle
        This list is usually of length 1. This list is longer only if more
        than one sample is taken for a particle.
        This list has length 0 if the particle is rejected.

    all_sum_stats: List[dict]
        List of all summary statistics generated during the creation of this
        particle (also when they led to rejection).
        This list is non-empty also for rejected particles.

    accepted: bool
        True if particle was accepted, False if not.
    """

    def __init__(self, m: int,
                 parameter: Parameter,
                 weight: float = 0,
                 accepted_distances: List[float] = None,
                 accepted_sum_stats: List[dict] = None,
                 all_sum_stats: List[dict] = None):

        self.m = m
        self.parameter = parameter
        self.weight = weight
        self.accepted_distances = accepted_distances
        self.accepted_sum_stats = accepted_sum_stats
        self.all_sum_stats = all_sum_stats

    @property
    def accepted(self):
        return len(self.accepted_sum_stats) > 0

    def __getitem__(self, item):
        return getattr(self, item)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def __eq__(self, other):
        for key in ["m", "parameter", "weight", "accepted_distances",
                    "accepted_sum_stats", "all_sum_stats"]:
            if self[key] != other[key]:
                return False
        return True

    def copy(self):
        return self.__class__(self.m, self.parameter, self.weight,
                              self.accepted_distances,
                              self.accepted_sum_stats, self.all_sum_stats)


class Population:
    """
    A population contains a list of particles and offers standardized access
    to them. Upon initialization, the particle weights are normalized and model
    probabilities computed as described in _normalize_weights.
    """

    def __init__(self, particles: List[Particle]):
        self._list = [particle.copy() for particle in particles]
        self._model_probabilities = None
        self._normalize_weights()

    def __len__(self):
        return len(self._list)

    def get_list(self) -> List[Particle]:
        """
        Get a copy of the underlying particle list.

        :return:
            A copied particle list.
        """

        return self._list.copy()

    def _normalize_weights(self):
        """
        Normalize the cumulative weight of the particles belonging to a model
        to 1, and compute the model probabilities. Should only be called once.
        """

        store = self.to_dict()

        model_total_weights = {m: sum(particle.weight for particle in plist)
                               for m, plist in store.items()}
        population_total_weight = sum(model_total_weights.values())
        model_probabilities = {m: w / population_total_weight
                               for m, w in model_total_weights.items()}

        # update model_probabilities attribute
        self._model_probabilities = model_probabilities

        # normalize weights within each model
        for m in store:
            model_total_weight = model_total_weights[m]
            plist = store[m]
            for particle in plist:
                particle.weight /= model_total_weight

    def update_distances(self,
                         distance_to_ground_truth: Callable[[dict], float]):
        """
        Update the distances of all summary statistics of all particles
        according to the passed distance function (which is typically
        different from the distance function with which the original
        distances were computed).

        :param distance_to_ground_truth:
            Distance function to the observed summary statistics.
        """

        for particle in self._list:
            for i in range(len(particle.accepted_distances)):
                particle.accepted_distances[i] = distance_to_ground_truth(
                    particle.accepted_sum_stats[i])

    def get_model_probabilities(self) -> dict:
        """
        Get probabilities of the individual models.
        :return:
        """

        # _model_probabilities are assigned during normalization
        return self._model_probabilities

    def get_weighted_distances(self) -> pandas.DataFrame:
        """
        Create iteration of distances and weights. All weights sum to 1.

        :return:
            A pandas.DataFrame containing in column 'distance' the distances
            and in column 'weight' the scaled weights.
        """

        # create pandas.DataFrame of distances and weights
        rows = []
        for particle in self._list:
            model_probability = self._model_probabilities[particle.m]
            for distance in particle.accepted_distances:
                rows.append({'distance': distance,
                             'w': particle.weight * model_probability})

        df = pandas.DataFrame(rows)
        return df

    def to_dict(self) -> dict:
        """
        Create a dictionary representation, creating a list of particles for
        each model.

        :return:
            A dictionary with the models as keys and a list of particles for
            each model as values.
        """

        store = dict()

        for particle in self._list:
            if particle is not None:
                # setdefault: similar to get(), sets dict[key] = default if key
                # is not in dict yet.
                store.setdefault(particle.m, []).append(particle)
            else:
                print("Warning: Empty particle.")

        return store