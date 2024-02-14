""" FSMActions used in unit tests """
import logging

from google.appengine.ext import db

from fantasm.action import DatastoreContinuationFSMAction, ContinuationFSMAction
from fantasm.constants import FORK_PARAM
from fantasm.constants import CONTINUATION_RESULT_KEY
from fantasm.constants import CONTINUATION_RESULTS_KEY
from fantasm.exceptions import HaltMachineError

# pylint: disable=C0111, W0613
# - docstrings not reqd in unit tests
# - these actions do not use arguments

class Custom:
    def __init__(self, string):
        self.impl = eval(string)
    def __repr__(self):
        return repr(self.impl)

class CustomImpl(Custom):
    def __init__(self, a=None, b=None): # pylint: disable=W0231
        self.a = a
        self.b = b
    def __repr__(self):
        return 'CustomImpl(a="{}", b="{}")'.format(self.a, self.b)
    def __eq__(self, other):
        # just for unit test equality
        if other.__class__ is Custom:
            other = other.impl
        return self.a == other.a and self.b == other.b
    def __ne__(self, other):
        # just for unit test inequality
        if other.__class__ is Custom:
            other = other.impl
        return self.a != other.a or self.b != other.b

class ContextRecorder:
    CONTEXTS = []
    def execute(self, context, obj):
        self.CONTEXTS.append(context)

class CountExecuteCalls:
    def __init__(self):
        self.count = 0
        self.fails = 0
    def execute(self, context, obj):
        self.count += 1
        if self.fails:
            self.fails -= 1
            raise Exception()
        return self.event
    @property
    def event(self):
        return 'next-event'

class CountExecuteCallsWithSpawn(CountExecuteCalls):
    def execute(self, context, obj):
        context.spawn('MachineToSpawn', [{'a': '1'}, {'b': '2'}])
        super().execute(context, obj)
        return None

class CountExecuteCallsWithFork:
    def __init__(self):
        self.count = 0
        self.fails = 0
        self.numFork = 0
    def execute(self, context, obj):
        self.count += 1
        if self.fails:
            self.fails -= 1
            raise Exception()
        context.fork()
        context.fork()
        return self.event
    @property
    def event(self):
        return 'next-event'

class CountExecuteAndContinuationCalls:
    def __init__(self):
        self.count = 0
        self.ccount = 0
        self.fails = 0
        self.failat = 0
        self.cfailat = 0
    def continuation(self, context, obj, token=None):
        self.ccount += 1
        if self.ccount == self.cfailat:
            raise Exception()
        return None
    def execute(self, context, obj):
        self.count += 1
        if self.count == self.failat:
            raise Exception()
        if self.fails:
            self.fails -= 1
            raise Exception()
        return self.event
    @property
    def event(self):
        return 'next-event'

class CountExecuteCallsFanInEntry:
    def __init__(self):
        self.count = 0
        self.fcount = 0
        self.fails = 0
    def execute(self, context, obj):
        if not isinstance(context, list):
            context = [context]
        self.count += 1
        self.fcount += len(context)
        if self.fails:
            self.fails -= 1
            raise Exception()
        return self.event
    @property
    def event(self):
        return None

class ResultModel( db.Model ):
    total = db.IntegerProperty()

class CountExecuteCallsFanIn(CountExecuteCallsFanInEntry):
    CONTEXTS = []
    def execute(self, context, obj):
        CountExecuteCallsFanIn.CONTEXTS.extend(context)
        result = ResultModel.get_by_key_name(context.instanceName)
        if not result:
            result = ResultModel(total=0, key_name=context.instanceName)
        result.total += sum([len(c.get('fan-me-in', [])) for c in context])
        result.put() # txn is overkill for this test
        return super().execute(context, obj)
    @property
    def event(self):
        return 'next-event'

class CountExecuteCallsFanInFinal(CountExecuteCallsFanIn):
    @property
    def event(self):
        return None

class CountExecuteCallsFinal(CountExecuteCalls):
    @property
    def event(self):
        return None

class CountExecuteCallsSelfTransition:
    def __init__(self):
        self.count = 0
        self.fails = 0
    def execute(self, context, obj):
        self.count += 1
        if self.fails:
            self.fails -= 1
            raise Exception()
        if self.count <= 5:
            return 'next-event1'
        else:
            return 'next-event2'

class RaiseExceptionAction:
    def execute(self, context, obj):
        raise Exception('instrumented exception')

class RaiseExceptionContinuationAction:
    def continuation(self, context, obj, token=None):
        return "token"
    def execute(self, context, obj):
        raise Exception('instrumented exception')

class RaiseHaltMachineErrorAction:
    def execute(self, context, obj):
        raise HaltMachineError('instrumented exception', logLevel=logging.DEBUG)

class RaiseHaltMachineErrorActionNoMessage:
    def execute(self, context, obj):
        raise HaltMachineError('instrumented exception', logLevel=None) # do not log

class RaiseHaltMachineErrorContinuationAction:
    def continuation(self, context, obj, token=None):
        raise HaltMachineError('instrumented exception', logLevel=logging.DEBUG)
    def execute(self, context, obj):
        return 'next-event'

class TestDatastoreContinuationFSMAction(DatastoreContinuationFSMAction):
    def __init__(self):
        super().__init__()
        self.count = 0
        self.ccount = 0
        self.fails = 0
        self.failat = 0
        self.cfailat = 0
    def getQuery(self, context, obj):
        return db.GqlQuery("SELECT * FROM TestModel ORDER BY prop1")
    def getBatchSize(self, context, obj):
        return 2
    def continuation(self, context, obj, token=None):
        self.ccount += 1
        if self.ccount == self.cfailat:
            raise Exception()
        return super().continuation(context, obj, token=token)
    def execute(self, context, obj):
        if not obj[CONTINUATION_RESULTS_KEY]:
            return None
        self.count += 1
        context['__count__'] = self.count
        context['fan-me-in'] = context.get('fan-me-in', []) + [r.key() for r in obj[CONTINUATION_RESULTS_KEY]]
        if self.count == self.failat:
            raise Exception()
        if self.fails:
            self.fails -= 1
            raise Exception()
        return 'next-event'

class TestDatastoreContinuationFSMActionFanInGroupFSMAction(TestDatastoreContinuationFSMAction):
    def execute(self, context, obj):
        if CONTINUATION_RESULTS_KEY in obj and obj[CONTINUATION_RESULTS_KEY]:
            context['fan-in-group'] = obj[CONTINUATION_RESULTS_KEY][0].key().id_or_name()
        return super().execute(context, obj)

class HappySadContinuationFSMAction(TestDatastoreContinuationFSMAction):
    def execute(self, context, obj):
        if not obj[CONTINUATION_RESULTS_KEY]:
            return None
        self.count += 1
        if self.count == self.failat:
            raise Exception()
        if self.fails:
            self.fails -= 1
            raise Exception()
        if self.count % 2:
            return 'happy'
        else:
            return 'sad'

class TestFileContinuationFSMAction(ContinuationFSMAction):
    CONTEXTS = []
    ENTRIES = ['a', 'b', 'c', 'd']
    def __init__(self):
        super().__init__()
        self.count = 0
        self.ccount = 0
        self.fails = 0
        self.failat = 0
        self.cfailat = 0
    def continuation(self, context, obj, token=None):
        token = int(token or 0) # awkward
        self.ccount += 1
        if self.ccount == self.cfailat:
            raise Exception()
        obj[CONTINUATION_RESULTS_KEY] = [TestFileContinuationFSMAction.ENTRIES[token]]
        nextToken = token + 1
        if nextToken >= len(TestFileContinuationFSMAction.ENTRIES):
            return None
        return nextToken
    def execute(self, context, obj):
        self.count += 1
        context[CONTINUATION_RESULT_KEY] = obj[CONTINUATION_RESULTS_KEY][0]
        TestFileContinuationFSMAction.CONTEXTS.append(context)
        if self.count == self.failat:
            raise Exception()
        if self.fails:
            self.fails -= 1
            raise Exception()
        return 'next-event'

class TestContinuationAndForkFSMAction(DatastoreContinuationFSMAction):
    def __init__(self):
        super().__init__()
        self.count = 0
        self.ccount = 0
        self.fails = 0
        self.failat = 0
        self.cfailat = 0
    def getQuery(self, context, obj):
        return db.GqlQuery("SELECT * FROM TestModel ORDER BY prop1")
    def getBatchSize(self, context, obj):
        return 2
    def continuation(self, context, obj, token=None):
        self.ccount += 1
        if self.ccount == self.cfailat:
            raise Exception()
        return super().continuation(context, obj, token=token)
    def execute(self, context, obj):
        if not obj[CONTINUATION_RESULTS_KEY]:
            return None
        self.count += 1
        context['__count__'] = self.count
        context['data'] = {'a': 'b'}
        if self.count == self.failat:
            raise Exception()
        if self.fails:
            self.fails -= 1
            raise Exception()

        # FIXME: this pattern is a bit awkward, or is it?
        # FIXME: how can we drive this into yaml?
        # FIXME: maybe just another provided base class like DatastoreContinuationFSMAction?

        # fork a machine to deal with all but one of the continuation dataset
        for result in obj[CONTINUATION_RESULTS_KEY][1:]:
            context.fork(data={'key': result.key()})

        # and deal with the leftover data item
        context['key'] = obj[CONTINUATION_RESULT_KEY].key()
        context[FORK_PARAM] = -1

        # this event will be dispatched to this machine an all the forked contexts
        return 'next-event'

class DoubleContinuation1(ContinuationFSMAction):
    CONTEXTS = []
    ENTRIES = ['1', '2', '3']
    def __init__(self):
        super().__init__()
        self.count = 0
        self.ccount = 0
    def continuation(self, context, obj, token=None):
        token = int(token or 0) # awkward
        self.ccount += 1
        obj[CONTINUATION_RESULTS_KEY] = [DoubleContinuation1.ENTRIES[token]]
        nextToken = token + 1
        if nextToken >= len(DoubleContinuation1.ENTRIES):
            return None
        return nextToken
    def execute(self, context, obj):
        self.count += 1
        context['c1'] = obj[CONTINUATION_RESULTS_KEY][0]
        #logging.critical('%s' % (context['c1']))
        DoubleContinuation1.CONTEXTS.append(context)
        return 'ok'

class DoubleContinuation2:
    CONTEXTS = []
    ENTRIES = ['a', 'b', 'c']
    def __init__(self):
        super().__init__()
        self.count = 0
        self.ccount = 0
    def continuation(self, context, obj, token=None):
        token = int(token or 0) # awkward
        self.ccount += 1
        obj[CONTINUATION_RESULTS_KEY] = [DoubleContinuation2.ENTRIES[token]]
        nextToken = token + 1
        if nextToken >= len(DoubleContinuation2.ENTRIES):
            return None
        return nextToken
    def execute(self, context, obj):
        self.count += 1
        context['c2'] = obj[CONTINUATION_RESULTS_KEY][0]
        #logging.critical('%s-%s' % (context['c1'], context['c2']))
        DoubleContinuation2.CONTEXTS.append(context)
        return 'okfinal'

class FSCEE_InitialState:
    def __init__(self):
        self.count = 0
    def execute(self, context, obj):
        self.count += 1
        return 'ok'

class FSCEE_OptionalFinalState:
    def __init__(self):
        self.count = 0
    def execute(self, context, obj):
        self.count += 1
        # a final state should be able to emit an event
        return 'ok'

class FSCEE_FinalState:
    def __init__(self):
        self.count = 0
    def execute(self, context, obj):
        self.count += 1
