import numpy as np


class OfflineEnv(object):
    def __init__(
        self,
        users_dict,
        users_history_lens,
        movies_id_to_movies,
        movies_groups,
        state_size,
        fairness_constraints,
        fix_user_id=None,
    ):

        # users: interacted items, rate
        self.users_dict = users_dict

        # users history length
        self.users_history_lens = users_history_lens

        # movies id : movies name
        self.items_id_to_name = movies_id_to_movies

        self.state_size = state_size

        # filter users with len_history > state_size
        self.available_users = self._generate_available_users()

        self.fix_user_id = fix_user_id

        self.user = (
            fix_user_id if fix_user_id else np.random.choice(self.available_users)
        )
        self.user_items = {data[0]: data[1] for data in self.users_dict[self.user]}
        self.items = [data[0] for data in self.users_dict[self.user][: self.state_size]]
        self.done = False
        self.recommended_items = set(self.items)
        self.done_count = 3000

        self.movies_groups = movies_groups
        self.group_count = {}
        self.total_recommended_items = 0
        self.fairness_constraints = fairness_constraints

    def _generate_available_users(self):
        available_users = []
        for i, length in zip(self.users_dict.keys(), self.users_history_lens):
            if length > self.state_size:
                available_users.append(i)
        return available_users

    def reset(self):
        self.user = (
            self.fix_user_id
            if self.fix_user_id
            else np.random.choice(self.available_users)
        )
        self.user_items = {data[0]: data[1] for data in self.users_dict[self.user]}
        self.items = [data[0] for data in self.users_dict[self.user][: self.state_size]]
        self.done = False
        self.recommended_items = set(self.items)
        self.group_count.clear()
        self.total_recommended_items = 0
        return self.user, self.items, self.done

    def step(self, action, top_k=False):

        reward = -2

        if top_k:
            correctly_recommended = []
            rewards = []
            for act in action:
                group = self.movies_groups[act + 1]
                if group not in self.group_count:
                    self.group_count[group] = 0
                self.group_count[group] += 1
                self.total_recommended_items += 1

                if act in self.user_items.keys() and act not in self.recommended_items:
                    correctly_recommended.append(act)

                    rew = (
                        (
                            self.fairness_constraints[group - 1]
                            / sum(self.fairness_constraints)
                        )
                        - (self.group_count[group] / self.total_recommended_items)
                        + 1
                    )
                    rewards.append(rew)  # 0.5 * (self.user_items[act] - 3))
                else:
                    rewards.append(-2)
                self.recommended_items.add(act)

            if max(rewards) > 0:
                self.items = (
                    self.items[len(correctly_recommended) :] + correctly_recommended
                )
                self.items = self.items[-self.state_size :]
            reward = rewards

        else:
            group = self.movies_groups[action + 1]
            if group not in self.group_count:
                self.group_count[group] = 0
            self.group_count[group] += 1
            self.total_recommended_items += 1

            if (
                action in self.user_items.keys()
                and action not in self.recommended_items
            ):
                rew = (
                    (
                        self.fairness_constraints[group - 1]
                        / sum(self.fairness_constraints)
                    )
                    - (self.group_count[group] / self.total_recommended_items)
                    + 1
                )
                reward = rew  # 0.5 * (self.user_items[action] - 3)  # reward
            if reward >= 0:
                self.items = self.items[1:] + [action]
            self.recommended_items.add(action)

        if (
            len(self.recommended_items) > self.done_count
            or len(self.recommended_items) >= self.users_history_lens[self.user - 1]
        ):
            self.done = True

        return self.items, reward, self.done, self.recommended_items

    def get_items_names(self, items_ids):
        items_names = []
        for id in items_ids:
            try:
                items_names.append(self.items_id_to_name[str(id)])
            except:
                items_names.append(list(["Not in list"]))
        return items_names
