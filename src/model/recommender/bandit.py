import numpy as np
import datetime
from dataclasses import dataclass, field
from obp.policy.base import BaseContextFreePolicy, BaseContextualPolicy
from obp.policy.logistic import BaseLogisticPolicy
from obp.utils import check_array

from sklearn.utils import check_random_state
from sklearn.utils import check_scalar
from typing import List


@dataclass
class EpsilonGreedy(BaseContextFreePolicy):
    """Epsilon Greedy policy.
    Parameters
    ----------
    n_actions: int
        Number of actions.
    len_list: int, default=1
        Length of a list of actions recommended in each impression.
        When Open Bandit Dataset is used, 3 should be set.
    batch_size: int, default=1
        Number of samples used in a batch parameter update.
    random_state: int, default=None
        Controls the random seed in sampling actions.
    epsilon: float, default=1.
        Exploration hyperparameter that must take value in the range of [0., 1.].
    policy_name: str, default=f'egreedy_{epsilon}'.
        Name of bandit policy.
    """

    epsilon: float = 1.0
    n_group: int = 0
    dim: int = 0

    def __post_init__(self) -> None:
        """Initialize Class."""
        check_scalar(self.epsilon, "epsilon", float, min_val=0.0, max_val=1.0)
        super().__post_init__()

        self.policy_name = f"egreedy_{self.epsilon}_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"

    def select_action(self, available_items=None) -> np.ndarray:
        """Select a list of actions.
        Returns
        ----------
        selected_actions: array-like, shape (len_list, )
            List of selected actions.
        """
        predicted_rewards = None
        n_actions = available_items if available_items else self.n_actions

        if (self.random_.rand() > self.epsilon) and (self.action_counts.min() > 0):
            predicted_rewards = self.reward_counts / self.action_counts
            predicted_rewards = predicted_rewards.argsort()
            if available_items:
                predicted_rewards = predicted_rewards[available_items]
            actions = predicted_rewards[::-1][: self.len_list]
        else:
            actions = self.random_.choice(n_actions, size=self.len_list, replace=False)

        return actions

    def update_params(self, action: int, reward: float) -> None:
        """Update policy parameters.
        Parameters
        ----------
        action: int
            Selected action by the policy.
        reward: float
            Observed reward for the chosen action and position.
        """
        self.n_trial += 1
        self.action_counts_temp[action] += 1
        self.reward_counts_temp[action] += reward
        if self.n_trial % self.batch_size == 0:
            self.action_counts = np.copy(self.action_counts_temp)


@dataclass
class BaseLinPolicy(BaseContextualPolicy):
    """Base class for contextual bandit policies using linear regression.
    Parameters
    ------------
    dim: int
        Number of dimensions of context vectors.
    n_actions: int
        Number of actions.
    len_list: int, default=1
        Length of a list of actions recommended in each impression.
        When Open Bandit Dataset is used, 3 should be set.
    batch_size: int, default=1
        Number of samples used in a batch parameter update.
    random_state: int, default=None
        Controls the random seed in sampling actions.
    epsilon: float, default=0.
        Exploration hyperparameter that must take value in the range of [0., 1.].
    """

    def __post_init__(self) -> None:
        """Initialize class."""
        super().__post_init__()

        self.theta_hat = np.zeros((self.dim, self.n_actions))
        self.A_inv = np.concatenate(
            [np.identity(self.dim) for _ in np.arange(self.n_actions)]
        ).reshape(self.n_actions, self.dim, self.dim)
        self.b = np.zeros((self.dim, self.n_actions))

        self.A_inv_temp = np.concatenate(
            [np.identity(self.dim) for _ in np.arange(self.n_actions)]
        ).reshape(self.n_actions, self.dim, self.dim)
        self.b_temp = np.zeros((self.dim, self.n_actions))

    def update_params(self, action: int, reward: float, context: np.ndarray) -> None:
        """Update policy parameters.
        Parameters
        ------------
        action: int
            Selected action by the policy.
        reward: float
            Observed reward for the chosen action and position.
        context: array-like, shape (1, dim_context)
            Observed context vector.
        """
        self.n_trial += 1
        self.action_counts[action] += 1

        # update the inverse matrix by the Woodbury formula
        self.A_inv_temp[action] -= (
            self.A_inv_temp[action]
            @ context.T
            @ context
            @ self.A_inv_temp[action]
            / (1 + context @ self.A_inv_temp[action] @ context.T)[0][0]
        )
        self.b_temp[:, action] += reward * context.flatten()
        if self.n_trial % self.batch_size == 0:
            self.A_inv, self.b = (
                np.copy(self.A_inv_temp),
                np.copy(self.b_temp),
            )


@dataclass
class LinUCB(BaseLinPolicy):
    """Linear Upper Confidence Bound.
    Parameters
    ----------
    dim: int
        Number of dimensions of context vectors.
    n_actions: int
        Number of actions.
    len_list: int, default=1
        Length of a list of actions recommended in each impression.
        When Open Bandit Dataset is used, 3 should be set.
    batch_size: int, default=1
        Number of samples used in a batch parameter update.
    random_state: int, default=None
        Controls the random seed in sampling actions.
    epsilon: float, default=0.
        Exploration hyperparameter that must be greater than or equal to 0.0.
    References
    --------------
    L. Li, W. Chu, J. Langford, and E. Schapire.
    A contextual-bandit approach to personalized news article recommendation.
    In Proceedings of the 19th International Conference on World Wide Web, pp. 661–670. ACM, 2010.
    """

    epsilon: float = 0.0

    def __post_init__(self) -> None:
        """Initialize class."""
        check_scalar(self.epsilon, "epsilon", float, min_val=0.0)
        super().__post_init__()

        self.policy_name = f"linear_ucb_{self.epsilon}_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"

    def select_action(self, context: np.ndarray, available_items=None) -> np.ndarray:
        """Select action for new data.
        Parameters
        ----------
        context: array
            Observed context vector.
        Returns
        ----------
        selected_actions: array-like, shape (len_list, )
            List of selected actions.
        """
        check_array(array=context, name="context", expected_dim=2)
        if context.shape[0] != 1:
            raise ValueError("Expected `context.shape[0] == 1`, but found it False")

        self.theta_hat = np.concatenate(
            [
                self.A_inv[i] @ self.b[:, i][:, np.newaxis]
                for i in np.arange(self.n_actions)
            ],
            axis=1,
        )  # dim * n_actions
        sigma_hat = np.concatenate(
            [
                np.sqrt(context @ self.A_inv[i] @ context.T)
                for i in np.arange(self.n_actions)
            ],
            axis=1,
        )  # 1 * n_actions
        ucb_scores = (context @ self.theta_hat + self.epsilon * sigma_hat).flatten()
        ucb_scores = ucb_scores.argsort()
        if available_items:
            ucb_scores = ucb_scores[available_items]
        actions = ucb_scores[::-1][: self.len_list]

        return actions


@dataclass
class FairLinUCB(LinUCB):
    """Linear Upper Confidence Bound.
    Parameters
    ----------
    dim: int
        Number of dimensions of context vectors.
    n_actions: int
        Number of actions.
    len_list: int, default=1
        Length of a list of actions recommended in each impression.
        When Open Bandit Dataset is used, 3 should be set.
    batch_size: int, default=1
        Number of samples used in a batch parameter update.
    random_state: int, default=None
        Controls the random seed in sampling actions.
    epsilon: float, default=0.
        Exploration hyperparameter that must be greater than or equal to 0.0.
    References
    --------------
    L. Li, W. Chu, J. Langford, and E. Schapire.
    A contextual-bandit approach to personalized news article recommendation.
    In Proceedings of the 19th International Conference on World Wide Web, pp. 661–670. ACM, 2010.
    """

    fairness_weight: list = field(default_factory=list)
    epsilon: float = 0.0
    alpha: float = 0.0

    def __post_init__(self) -> None:
        """Initialize class."""
        check_scalar(self.epsilon, "epsilon", float, min_val=0.0)
        super().__post_init__()

        self.policy_name = f"fair_linear_ucb_{self.alpha}_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"

    def calculate_score_fairness(self) -> np.array:
        fair = (
            np.array(self.fairness_weight) * (np.sum(self.action_counts) - 1)
            - self.action_counts
        )

        return fair[~(fair < self.alpha)]

    def select_action(self, context: np.ndarray, available_items=None) -> np.ndarray:
        """Select action for new data.
        Parameters
        ----------
        context: array
            Observed context vector.
        Returns
        ----------
        selected_actions: array-like, shape (len_list, )
            List of selected actions.
        """
        check_array(array=context, name="context", expected_dim=2)
        if context.shape[0] != 1:
            raise ValueError("Expected `context.shape[0] == 1`, but found it False")

        A = self.calculate_score_fairness()
        if len(A) > 0:
            actions = [int(np.argmax(A))]
        else:
            self.theta_hat = np.concatenate(
                [
                    self.A_inv[i] @ self.b[:, i][:, np.newaxis]
                    for i in np.arange(self.n_actions)
                ],
                axis=1,
            )  # dim * n_actions
            sigma_hat = np.concatenate(
                [
                    np.sqrt(context @ self.A_inv[i] @ context.T)
                    for i in np.arange(self.n_actions)
                ],
                axis=1,
            )  # 1 * n_actions
            ucb_scores = (context @ self.theta_hat + self.epsilon * sigma_hat).flatten()
            actions = ucb_scores.argsort()[::-1][: self.len_list]

        return actions
