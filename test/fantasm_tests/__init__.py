""" Tests for fantasm. """

# pylint: disable=C0111
# - docstrings not reqd in unit tests

# The following three classes are here to test namespace overriding.
class MockAction2:
    def execute(self, context, obj):
        pass
class MockEntry2:
    def execute(self, context, obj):
        pass
class MockExit2:
    def execute(self, context, obj):
        pass
