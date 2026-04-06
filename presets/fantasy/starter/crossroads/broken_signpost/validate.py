"""Validator for the Broken Signpost puzzle."""


def validate(solution_fn):
    """The solution function should sort celestial symbols in the correct order.

    The correct order is: sun first (source of light), moon second (reflects sun),
    star last (most distant).
    """
    assert solution_fn(["moon", "star", "sun"]) == ["sun", "moon", "star"]
    assert solution_fn(["star", "sun", "moon"]) == ["sun", "moon", "star"]
    assert solution_fn(["sun", "moon", "star"]) == ["sun", "moon", "star"]
    return True
