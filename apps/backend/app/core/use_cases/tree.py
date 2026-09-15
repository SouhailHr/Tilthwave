from datetime import date

from common.dates import utc_now
from core.entities.tree import Tree as TreeEntity
from core.use_cases.base import BaseUseCase


class TreeUseCase(BaseUseCase):
    ENTITY = TreeEntity

    def get_trees_varieties(self):
        """
         this method gets a list of trees varieties
        @return: a list of trees varieties
        """
        trees = self.filter()
        trees_varieties = []
        for tree in trees:
            if tree.variety not in trees_varieties:
                trees_varieties.append(tree.variety)
        return trees_varieties

    def get_tree_average_age(self):
        """
        This method calculates the average age of the trees.
        @return: tree average age
        """
        trees = self.filter()
        if not trees:
            return "no trees"
        today = utc_now().date()
        total_age_in_days = sum((today - date.fromisoformat(str(tree.planting_date))).days for tree in trees)
        average_age_in_days = total_age_in_days / len(trees)

        if average_age_in_days < 30:
            return f"{int(average_age_in_days)} days"
        elif 30 <= average_age_in_days < 360:
            months = int(average_age_in_days / 30)
            remaining_days = int(average_age_in_days % 30)
            return (
                f"{months} month{'s' if months > 1 else ''} and {remaining_days} day{'s' if remaining_days > 1 else ''}"
            )
        else:
            years = int(average_age_in_days / 360)
            remaining_days = int(average_age_in_days % 360)
            months = int(remaining_days / 30)
            remaining_days %= 30
            return (
                f"{years} year{'s' if years > 1 else ''}, {months} month{'s' if months > 1 else ''},"
                f" and {remaining_days} day{'s' if remaining_days > 1 else ''}"
            )

    def get_stats(self):
        """
         this method gets the stats of the trees
        @return: dict that has the stats of the trees
        eg : stats_dict {
            "total_trees": 10,
            "total_varieties": 3,
            "tree_average_age": 10 months and 9 days
        }
        """
        trees = self.filter()
        trees_varieties = self.get_trees_varieties()

        total_trees = len(trees) if trees else 0

        total_trees_varieties = (
            f"{len(trees_varieties)} trees varieties: {', '.join(trees_varieties)}"
            if trees_varieties
            else "No varieties found"
        )

        total_trees_varieties = total_trees_varieties
        tree_average_age = self.get_tree_average_age()
        stats_dict = {
            "total_trees": total_trees,
            "total_varieties": total_trees_varieties,
            "tree_average_age": tree_average_age,
        }

        return stats_dict
