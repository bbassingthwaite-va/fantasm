""" Tests for fantasm.config """

import unittest
from google.appengine.ext import db
from fantasm import config, exceptions, constants
import fantasm_tests
from fantasm_tests.helpers import getLoggingDouble

from minimock import restore

# pylint: disable=C0111, W0212
# - docstrings not reqd in unit tests
# - accessing protected config members a lot in these tests

# the following classes are used for namespace and interface testing
class MockAction:
    def execute(self, context, obj):
        pass
class MockEntry:
    def execute(self, context, obj):
        pass
class MockExit:
    def execute(self, context, obj):
        pass
class MockActionWithContinuation:
    def continuation(self, context, obj, token):
        pass
    def execute(self, context, obj):
        pass
class MockActionNoExecute:
    pass
class MockEntryNoExecute:
    pass
class MockExitNoExecute:
    pass

class TestMachineDictionaryProcessing(unittest.TestCase):

    def setUp(self):
        super().setUp()
        self.machineName = 'MyMachine'
        self.machineDict = {constants.MACHINE_NAME_ATTRIBUTE: self.machineName}

    def tearDown(self):
        super().tearDown()
        restore()

    def test_nameParsed(self):
        fsm = config._MachineConfig(self.machineDict)
        self.assertEqual(fsm.name, self.machineName)

    def test_nameRequired(self):
        self.assertRaises(exceptions.MachineNameRequiredError, config._MachineConfig, {})

    def test_nameFollowsNamingConvention(self):
        machineName = 'My_Bad_Machine_Name'
        self.assertRaises(exceptions.InvalidMachineNameError, config._MachineConfig,
                          {constants.MACHINE_NAME_ATTRIBUTE: machineName})

    def test_nameFollowsLengthRestriction(self):
        machineName = 'a'*(constants.MAX_NAME_LENGTH+1)
        self.assertRaises(exceptions.InvalidMachineNameError, config._MachineConfig,
                          {constants.MACHINE_NAME_ATTRIBUTE: machineName})

    def test_use_datastore_semaphore_parsed(self):
        useRunOnceSemaphore = not constants.DEFAULT_USE_RUN_ONCE_SEMAPHORE
        self.machineDict[constants.MACHINE_USE_RUN_ONCE_SEMAPHORE_ATTRIBUTE] = useRunOnceSemaphore
        fsm = config._MachineConfig(self.machineDict)
        self.assertEqual(useRunOnceSemaphore, fsm.useRunOnceSemaphore)

    def test_use_datastore_semaphore_hasDefaultValue(self):
        fsm = config._MachineConfig(self.machineDict)
        self.assertEqual(constants.DEFAULT_USE_RUN_ONCE_SEMAPHORE, fsm.useRunOnceSemaphore)

    def test_queueParsed(self):
        queueName = 'SomeQueue'
        self.machineDict[constants.QUEUE_NAME_ATTRIBUTE] = queueName
        fsm = config._MachineConfig(self.machineDict)
        self.assertEqual(fsm.queueName, queueName)

    def test_queueHasDefaultValue(self):
        fsm = config._MachineConfig(self.machineDict)
        self.assertEqual(fsm.queueName, constants.DEFAULT_QUEUE_NAME)

    def test_countdownParsed(self):
        countdown = 100
        self.machineDict[constants.COUNTDOWN_ATTRIBUTE] = countdown
        fsm = config._MachineConfig(self.machineDict)
        self.assertEqual(fsm.countdown, countdown)

    def test_countdownHasDefaultValue(self):
        fsm = config._MachineConfig(self.machineDict)
        self.assertEqual(fsm.countdown, constants.DEFAULT_COUNTDOWN)

    def test_targetParsed(self):
        target = 'some-target'
        self.machineDict[constants.TARGET_ATTRIBUTE] = target
        fsm = config._MachineConfig(self.machineDict)
        self.assertEqual(fsm.target, target)

    def test_targetHasDefaultValue(self):
        fsm = config._MachineConfig(self.machineDict)
        self.assertEqual(fsm.target, constants.DEFAULT_TARGET)

    def test_noNamespaceYieldNoneAttribute(self):
        fsm = config._MachineConfig(self.machineDict)
        self.assertEqual(fsm.namespace, None)

    def test_namespaceParsed(self):
        namespace = 'MyNamespace'
        self.machineDict[constants.NAMESPACE_ATTRIBUTE] = namespace
        fsm = config._MachineConfig(self.machineDict)
        self.assertEqual(fsm.namespace, namespace)

    def test_maxRetriesInvalidRaisesException(self):
        self.machineDict[constants.MAX_RETRIES_ATTRIBUTE] = 'abc'
        self.assertRaises(exceptions.InvalidMaxRetriesError, config._MachineConfig, self.machineDict)

    def test_maxRetriesParsed(self):
        self.machineDict[constants.MAX_RETRIES_ATTRIBUTE] = '3'
        fsm = config._MachineConfig(self.machineDict)
        self.assertEqual(fsm.maxRetries, 3)

    def test_maxRetriesDefault(self):
        fsm = config._MachineConfig(self.machineDict)
        self.assertEqual(fsm.maxRetries, constants.DEFAULT_TASK_RETRY_LIMIT)

    def test_maxRetriesIssuesDeprecationWarning(self):
        loggingDouble = getLoggingDouble()
        self.machineDict[constants.MAX_RETRIES_ATTRIBUTE] = '3'
        fsm = config._MachineConfig(self.machineDict)
        self.assertTrue(fsm)
        self.assertEqual(loggingDouble.count['warning'], 1)

    def test_taskRetryLimitInvalidRaisesException(self):
        self.machineDict[constants.TASK_RETRY_LIMIT_ATTRIBUTE] = 'abc'
        self.assertRaises(exceptions.InvalidTaskRetryLimitError, config._MachineConfig, self.machineDict)

    def test_taskRetryLimitParsed(self):
        self.machineDict[constants.TASK_RETRY_LIMIT_ATTRIBUTE] = '3'
        fsm = config._MachineConfig(self.machineDict)
        self.assertEqual(fsm.taskRetryLimit, 3)

    def test_taskRetryLimitDefault(self):
        fsm = config._MachineConfig(self.machineDict)
        self.assertEqual(fsm.taskRetryLimit, constants.DEFAULT_TASK_RETRY_LIMIT)

    def test_maxRetriesAndTaskRetryLimitRaisesConfigurationError(self):
        self.machineDict[constants.TASK_RETRY_LIMIT_ATTRIBUTE] = '3'
        self.machineDict[constants.MAX_RETRIES_ATTRIBUTE] = '3'
        self.assertRaises(exceptions.MaxRetriesAndTaskRetryLimitMutuallyExclusiveError,
                          config._MachineConfig, self.machineDict)

    def test_settingTaskRetryLimitSetsMaxRetries(self):
        """ taskRetryLimit and maxRetries should be set to the same value. """
        self.machineDict[constants.TASK_RETRY_LIMIT_ATTRIBUTE] = '3'
        fsm = config._MachineConfig(self.machineDict)
        self.assertEqual(fsm.maxRetries, 3)

    def test_settingMaxRetriesSetsTaskRetryLimit(self):
        """ maxRetries and taskRetryLimit should be set to the same value. """
        self.machineDict[constants.MAX_RETRIES_ATTRIBUTE] = '3'
        fsm = config._MachineConfig(self.machineDict)
        self.assertEqual(fsm.taskRetryLimit, 3)

    def test_minBackoffSecondsParsed(self):
        self.machineDict[constants.MIN_BACKOFF_SECONDS_ATTRIBUTE] = '3'
        fsm = config._MachineConfig(self.machineDict)
        self.assertEqual(fsm.minBackoffSeconds, 3)

    def test_minBackoffSecondsDefault(self):
        fsm = config._MachineConfig(self.machineDict)
        self.assertEqual(fsm.minBackoffSeconds, constants.DEFAULT_MIN_BACKOFF_SECONDS)

    def test_minBackoffSecondsInvalidRaisesException(self):
        self.machineDict[constants.MIN_BACKOFF_SECONDS_ATTRIBUTE] = 'abc'
        self.assertRaises(exceptions.InvalidMinBackoffSecondsError, config._MachineConfig, self.machineDict)

    def test_maxBackoffSecondsParsed(self):
        self.machineDict[constants.MAX_BACKOFF_SECONDS_ATTRIBUTE] = '3'
        fsm = config._MachineConfig(self.machineDict)
        self.assertEqual(fsm.maxBackoffSeconds, 3)

    def test_maxBackoffSecondsDefault(self):
        fsm = config._MachineConfig(self.machineDict)
        self.assertEqual(fsm.maxBackoffSeconds, constants.DEFAULT_MAX_BACKOFF_SECONDS)

    def test_maxBackoffSecondsInvalidRaisesException(self):
        self.machineDict[constants.MAX_BACKOFF_SECONDS_ATTRIBUTE] = 'abc'
        self.assertRaises(exceptions.InvalidMaxBackoffSecondsError, config._MachineConfig, self.machineDict)

    def test_taskAgeLimitParsed(self):
        self.machineDict[constants.TASK_AGE_LIMIT_ATTRIBUTE] = '3'
        fsm = config._MachineConfig(self.machineDict)
        self.assertEqual(fsm.taskAgeLimit, 3)

    def test_taskAgeLimitDefault(self):
        fsm = config._MachineConfig(self.machineDict)
        self.assertEqual(fsm.taskAgeLimit, constants.DEFAULT_TASK_AGE_LIMIT)

    def test_taskAgeLimitInvalidRaisesException(self):
        self.machineDict[constants.TASK_AGE_LIMIT_ATTRIBUTE] = 'abc'
        self.assertRaises(exceptions.InvalidTaskAgeLimitError, config._MachineConfig, self.machineDict)

    def test_maxDoublingsParsed(self):
        self.machineDict[constants.MAX_DOUBLINGS_ATTRIBUTE] = '3'
        fsm = config._MachineConfig(self.machineDict)
        self.assertEqual(fsm.maxDoublings, 3)

    def test_maxDoublingsDefault(self):
        fsm = config._MachineConfig(self.machineDict)
        self.assertEqual(fsm.maxDoublings, constants.DEFAULT_MAX_DOUBLINGS)

    def test_maxDoublingsInvalidRaisesException(self):
        self.machineDict[constants.MAX_DOUBLINGS_ATTRIBUTE] = 'abc'
        self.assertRaises(exceptions.InvalidMaxDoublingsError, config._MachineConfig, self.machineDict)

    def test_invalidAttributeRaisesException(self):
        self.machineDict['bad_attribute'] = 'something'
        self.assertRaises(exceptions.InvalidMachineAttributeError, config._MachineConfig, self.machineDict)

    def test_contextTypesDefault(self):
        fsm = config._MachineConfig(self.machineDict)
        self.assertEqual(fsm.contextTypes, {})

    def test_contextTypesParsed(self):
        self.machineDict[constants.MACHINE_CONTEXT_TYPES_ATTRIBUTE] = {
            'counter': 'types.IntType'
        }
        fsm = config._MachineConfig(self.machineDict)
        self.assertEqual(1, len(fsm.contextTypes))
        self.assertTrue('counter' in fsm.contextTypes)

    def test_contextTypesValueResolved(self):
        self.machineDict[constants.MACHINE_CONTEXT_TYPES_ATTRIBUTE] = {
            'counter': 'types.IntType',
            'batch-key': 'google.appengine.ext.db.Key'
        }
        fsm = config._MachineConfig(self.machineDict)
        self.assertEqual(int, fsm.contextTypes['counter'])
        self.assertEqual(db.Key, fsm.contextTypes['batch-key'])

    def test_contextTypesBadValueRaisesException(self):
        self.machineDict[constants.NAMESPACE_ATTRIBUTE] = 'namespace'
        self.machineDict[constants.MACHINE_CONTEXT_TYPES_ATTRIBUTE] = {
            'counter': 'NeverHeardOfIt'
        }
        self.assertRaises(exceptions.UnknownModuleError, config._MachineConfig, self.machineDict)

class TestStateDictionaryProcessing(unittest.TestCase):

    def setUp(self):
        super().setUp()
        self.machineName = 'MyFsm'
        self.fsm = config._MachineConfig({constants.MACHINE_NAME_ATTRIBUTE: self.machineName})
        self.stateDict = {constants.STATE_NAME_ATTRIBUTE: 'MyState',
                          constants.STATE_ACTION_ATTRIBUTE: 'MockAction',
                          constants.NAMESPACE_ATTRIBUTE: 'fantasm_tests.config_test'}

    def tearDown(self):
        super().tearDown()
        restore()

    def test_nameParsed(self):
        state = self.fsm.addState(self.stateDict)
        self.assertEqual(state.name, self.stateDict[constants.STATE_NAME_ATTRIBUTE])

    def test_nameRequired(self):
        self.stateDict.pop(constants.STATE_NAME_ATTRIBUTE)
        self.assertRaises(exceptions.StateNameRequiredError, self.fsm.addState, self.stateDict)

    def test_nameFollowsNamingConvention(self):
        self.stateDict[constants.STATE_NAME_ATTRIBUTE] = 'bad_name'
        self.assertRaises(exceptions.InvalidStateNameError, self.fsm.addState, self.stateDict)

    def test_nameFollowsLengthRestriction(self):
        self.stateDict[constants.STATE_NAME_ATTRIBUTE] = 'a'*(constants.MAX_NAME_LENGTH+1)
        self.assertRaises(exceptions.InvalidStateNameError, self.fsm.addState, self.stateDict)

    def test_nameIsUnique(self):
        self.fsm.addState(self.stateDict)
        self.assertRaises(exceptions.StateNameNotUniqueError, self.fsm.addState, self.stateDict)

    def test_actionRequired(self):
        self.stateDict.pop(constants.STATE_ACTION_ATTRIBUTE)
        self.assertRaises(exceptions.StateActionRequired, self.fsm.addState, self.stateDict)

    def test_initialDefaultsToFalse(self):
        state = self.fsm.addState(self.stateDict)
        self.assertEqual(state.initial, False)

    def test_initialParsed(self):
        self.stateDict[constants.STATE_INITIAL_ATTRIBUTE] = True
        state = self.fsm.addState(self.stateDict)
        self.assertEqual(state.initial, True)

    def test_finalDefaultsToFalse(self):
        state = self.fsm.addState(self.stateDict)
        self.assertEqual(state.final, False)

    def test_finalParsed(self):
        self.stateDict[constants.STATE_FINAL_ATTRIBUTE] = True
        state = self.fsm.addState(self.stateDict)
        self.assertEqual(state.final, True)

    def test_continuationDefaultsToFalse(self):
        state = self.fsm.addState(self.stateDict)
        self.assertEqual(state.continuation, False)

    def test_continuationParsed(self):
        self.stateDict[constants.STATE_ACTION_ATTRIBUTE] = 'MockActionWithContinuation'
        self.stateDict[constants.STATE_CONTINUATION_ATTRIBUTE] = True
        state = self.fsm.addState(self.stateDict)
        self.assertEqual(state.continuation, True)

    def test_entryResolvedUsingDefaultNamespace(self):
        self.stateDict[constants.STATE_ENTRY_ATTRIBUTE] = 'MockEntry'
        state = self.fsm.addState(self.stateDict)
        self.assertEqual(fantasm_tests.config_test.MockEntry, state.entry.__class__)

    def test_exitResolvedUsingDefaultNamespace(self):
        self.stateDict[constants.STATE_EXIT_ATTRIBUTE] = 'MockExit'
        state = self.fsm.addState(self.stateDict)
        self.assertEqual(fantasm_tests.config_test.MockExit, state.exit.__class__)

    def test_actionResolvedUsingDefaultNamespace(self):
        state = self.fsm.addState(self.stateDict)
        self.assertEqual(fantasm_tests.config_test.MockAction, state.action.__class__)

    def test_entryResolvedUsingFullyQualified(self):
        self.stateDict[constants.STATE_ENTRY_ATTRIBUTE] = 'fantasm_tests.MockEntry2'
        state = self.fsm.addState(self.stateDict)
        self.assertEqual(fantasm_tests.MockEntry2, state.entry.__class__)

    def test_exitResolvedUsingFullyQualified(self):
        self.stateDict[constants.STATE_EXIT_ATTRIBUTE] = 'fantasm_tests.MockExit2'
        state = self.fsm.addState(self.stateDict)
        self.assertEqual(fantasm_tests.MockExit2, state.exit.__class__)

    def test_actionResolvedUsingFullyQualified(self):
        self.stateDict[constants.STATE_ACTION_ATTRIBUTE] = 'fantasm_tests.MockAction2'
        state = self.fsm.addState(self.stateDict)
        self.assertEqual(fantasm_tests.MockAction2, state.action.__class__)

    def test_entryResolvedUsingStateOverride(self):
        self.stateDict[constants.NAMESPACE_ATTRIBUTE] = 'fantasm_tests'
        self.stateDict[constants.STATE_ENTRY_ATTRIBUTE] = 'MockEntry2'
        self.stateDict[constants.STATE_ACTION_ATTRIBUTE] = 'MockAction2'
        state = self.fsm.addState(self.stateDict)
        self.assertEqual(fantasm_tests.MockEntry2, state.entry.__class__)

    def test_exitResolvedUsingStateOverride(self):
        self.stateDict[constants.NAMESPACE_ATTRIBUTE] = 'fantasm_tests'
        self.stateDict[constants.STATE_EXIT_ATTRIBUTE] = 'MockExit2'
        self.stateDict[constants.STATE_ACTION_ATTRIBUTE] = 'MockAction2'
        state = self.fsm.addState(self.stateDict)
        self.assertEqual(fantasm_tests.MockExit2, state.exit.__class__)

    def test_actionResolvedUsingStateOverride(self):
        self.stateDict[constants.NAMESPACE_ATTRIBUTE] = 'fantasm_tests'
        self.stateDict[constants.STATE_ACTION_ATTRIBUTE] = 'MockAction2'
        state = self.fsm.addState(self.stateDict)
        self.assertEqual(fantasm_tests.MockAction2, state.action.__class__)

    def test_noEntryYieldsNoneEntry(self):
        state = self.fsm.addState(self.stateDict)
        self.assertEqual(state.entry, None)

    def test_noExitYieldsNoneExit(self):
        state = self.fsm.addState(self.stateDict)
        self.assertEqual(state.exit, None)

    def test_unresolvedEntryYieldsException(self):
        self.stateDict[constants.STATE_ENTRY_ATTRIBUTE] = 'VeryBadClass'
        self.assertRaises(exceptions.UnknownClassError, self.fsm.addState, self.stateDict)

    def test_unresolvedExitYieldsException(self):
        self.stateDict[constants.STATE_EXIT_ATTRIBUTE] = 'VeryBadClass'
        self.assertRaises(exceptions.UnknownClassError, self.fsm.addState, self.stateDict)

    def test_unresolvedActionYieldsException(self):
        self.stateDict[constants.STATE_ACTION_ATTRIBUTE] = 'VeryBadClass'
        self.assertRaises(exceptions.UnknownClassError, self.fsm.addState, self.stateDict)

    def test_unresolvedActionBadClassYieldsException(self):
        self.stateDict[constants.NAMESPACE_ATTRIBUTE] = 'bad.namespace'
        self.assertRaises(exceptions.UnknownModuleError, self.fsm.addState, self.stateDict)

    def test_invalidAttributeRaisesException(self):
        self.stateDict['bad_attribute'] = 'something'
        self.assertRaises(exceptions.InvalidStateAttributeError, self.fsm.addState, self.stateDict)

    def test_continuationSpecifiedButNoContinuationMethodRaisesException(self):
        self.stateDict[constants.STATE_CONTINUATION_ATTRIBUTE] = True
        self.assertRaises(exceptions.InvalidContinuationInterfaceError, self.fsm.addState, self.stateDict)

    def test_continuationNotSpecifiedButHasContinuationMethodLogsWarning(self):
        loggingDouble = getLoggingDouble()
        self.stateDict[constants.STATE_CONTINUATION_ATTRIBUTE] = False
        self.stateDict[constants.STATE_ACTION_ATTRIBUTE] = 'MockActionWithContinuation'
        self.fsm.addState(self.stateDict)
        self.assertEqual(loggingDouble.count['warning'], 1)

    def test_actionSpecifiedButNoExecuteMethodRaisesException(self):
        self.stateDict[constants.STATE_ACTION_ATTRIBUTE] = 'MockActionNoExecute'
        self.assertRaises(exceptions.InvalidActionInterfaceError, self.fsm.addState, self.stateDict)

    def test_entrySpecifiedButNoExecuteMethodRaisesException(self):
        self.stateDict[constants.STATE_ENTRY_ATTRIBUTE] = 'MockEntryNoExecute'
        self.assertRaises(exceptions.InvalidEntryInterfaceError, self.fsm.addState, self.stateDict)

    def test_exitSpecifiedButNoExecuteMethodRaisesException(self):
        self.stateDict[constants.STATE_EXIT_ATTRIBUTE] = 'MockExitNoExecute'
        self.assertRaises(exceptions.InvalidExitInterfaceError, self.fsm.addState, self.stateDict)

    def test_faninDefaultToNoFanIn(self):
        state = self.fsm.addState(self.stateDict)
        self.assertEqual(state.fanInPeriod, constants.NO_FAN_IN)

    def test_faninMustBeAnInteger(self):
        self.stateDict[constants.STATE_FAN_IN_ATTRIBUTE] = 'abc'
        self.assertRaises(exceptions.InvalidFanInError, self.fsm.addState, self.stateDict)

    def test_faninGroupRequiresFanIn(self):
        self.stateDict[constants.STATE_FAN_IN_GROUP_ATTRIBUTE] = 'abc'
        self.assertRaises(exceptions.InvalidFanInGroupError, self.fsm.addState, self.stateDict)

    def test_faninParsed(self):
        self.stateDict[constants.STATE_FAN_IN_ATTRIBUTE] = 10
        state = self.fsm.addState(self.stateDict)
        self.assertEqual(state.fanInPeriod, 10)

    def test_faninCombinedWithContinuationRaisesException(self):
        self.stateDict[constants.STATE_FAN_IN_ATTRIBUTE] = 10
        self.stateDict[constants.STATE_CONTINUATION_ATTRIBUTE] = True
        self.stateDict[constants.STATE_ACTION_ATTRIBUTE] = 'MockActionWithContinuation'
        self.assertRaises(exceptions.FanInContinuationNotSupportedError, self.fsm.addState, self.stateDict)

    def test_exitActionOnContinuationRaisesException(self):
        self.stateDict[constants.STATE_CONTINUATION_ATTRIBUTE] = True
        self.stateDict[constants.STATE_ACTION_ATTRIBUTE] = 'MockActionWithContinuation'
        self.stateDict[constants.STATE_EXIT_ATTRIBUTE] = 'MockExit'
        self.assertRaises(exceptions.UnsupportedConfigurationError, self.fsm.addState, self.stateDict)

    def test_exitActionOnFanInRaisesException(self):
        self.stateDict[constants.STATE_FAN_IN_ATTRIBUTE] = 10
        self.stateDict[constants.STATE_EXIT_ATTRIBUTE] = 'MockExit'
        self.assertRaises(exceptions.UnsupportedConfigurationError, self.fsm.addState, self.stateDict)

class TestMachineUrlConstruction(unittest.TestCase):

    def test_urlIncludesHostName(self):
        fsm = config._MachineConfig({constants.MACHINE_NAME_ATTRIBUTE: 'MyMachine'})
        self.assertEqual(fsm.url, '%sfsm/MyMachine/' % constants.DEFAULT_ROOT_URL)

    def test_rootUrlOverridesDefault(self):
        fsm = config._MachineConfig({constants.MACHINE_NAME_ATTRIBUTE: 'MyMachine'}, rootUrl='/myfsm')
        self.assertEqual(fsm.url, '/myfsm/fsm/MyMachine/')

class TestTransitionDictionaryProcessing(unittest.TestCase):

    def setUp(self):
        super().setUp()
        self.transDict = {
            constants.TRANS_EVENT_ATTRIBUTE: 'MyEvent',
            constants.TRANS_TO_ATTRIBUTE: 'GoodState'
        }
        self.fsm = config._MachineConfig({constants.MACHINE_NAME_ATTRIBUTE: 'MyMachine',
                                          constants.NAMESPACE_ATTRIBUTE: 'fantasm_tests.config_test',
                                          constants.QUEUE_NAME_ATTRIBUTE: 'somequeue',
                                          constants.COUNTDOWN_ATTRIBUTE: 100,
                                          constants.TARGET_ATTRIBUTE: 'some-target',
                                          constants.TASK_RETRY_LIMIT_ATTRIBUTE: 100,
                                          constants.MIN_BACKOFF_SECONDS_ATTRIBUTE: 101,
                                          constants.MAX_BACKOFF_SECONDS_ATTRIBUTE: 102,
                                          constants.TASK_AGE_LIMIT_ATTRIBUTE: 103,
                                          constants.MAX_DOUBLINGS_ATTRIBUTE: 104})
        self.goodState = self.fsm.addState({constants.STATE_NAME_ATTRIBUTE: 'GoodState',
                                            constants.STATE_ACTION_ATTRIBUTE: 'MockAction'})

    def test_nameGenerated(self):
        transition = self.fsm.addTransition(self.transDict, 'GoodState')
        self.assertEqual(transition.name, 'GoodState--MyEvent')

    def test_eventRequired(self):
        self.transDict.pop(constants.TRANS_EVENT_ATTRIBUTE)
        self.assertRaises(exceptions.TransitionEventRequiredError, self.fsm.addTransition, self.transDict, 'GoodState')

    def test_eventFollowingNamingConvention(self):
        self.transDict[constants.TRANS_EVENT_ATTRIBUTE] = 'bad_name'
        self.assertRaises(exceptions.InvalidTransitionEventNameError,
                          self.fsm.addTransition, self.transDict, 'GoodState')

    def test_eventFollowsLengthRestriction(self):
        self.transDict[constants.TRANS_EVENT_ATTRIBUTE] = 'a'*(constants.MAX_NAME_LENGTH+1)
        self.assertRaises(exceptions.InvalidTransitionEventNameError,
                          self.fsm.addTransition, self.transDict, 'GoodState')

    def test_eventParsed(self):
        transition = self.fsm.addTransition(self.transDict, 'GoodState')
        self.assertEqual(transition.event, self.transDict[constants.TRANS_EVENT_ATTRIBUTE])

    def test_toRequired(self):
        self.transDict.pop(constants.TRANS_TO_ATTRIBUTE)
        self.assertRaises(exceptions.TransitionToRequiredError, self.fsm.addTransition, self.transDict, 'GoodState')

    def test_toUnknownRaisesException(self):
        self.transDict[constants.TRANS_TO_ATTRIBUTE] = 'UnknownState'
        self.assertRaises(exceptions.TransitionUnknownToStateError, self.fsm.addTransition, self.transDict, 'GoodState')

    def test_toParsed(self):
        transition = self.fsm.addTransition(self.transDict, 'GoodState')
        self.assertEqual(transition.toState, self.goodState)

    def test_noActionYieldsNoneAttribute(self):
        transition = self.fsm.addTransition(self.transDict, 'GoodState')
        self.assertEqual(transition.action, None)

    def test_actionResolvedUsingDefaultNamespace(self):
        self.transDict[constants.TRANS_ACTION_ATTRIBUTE] = 'MockAction'
        transition = self.fsm.addTransition(self.transDict, 'GoodState')
        self.assertEqual(fantasm_tests.config_test.MockAction, transition.action.__class__)

    def test_actionResolvedUsingFullyQualified(self):
        self.transDict[constants.TRANS_ACTION_ATTRIBUTE] = 'fantasm_tests.MockAction2'
        transition = self.fsm.addTransition(self.transDict, 'GoodState')
        self.assertEqual(fantasm_tests.MockAction2, transition.action.__class__)

    def test_actionResolvedUsingStateOverride(self):
        self.transDict[constants.NAMESPACE_ATTRIBUTE] = 'fantasm_tests'
        self.transDict[constants.TRANS_ACTION_ATTRIBUTE] = 'MockAction2'
        transition = self.fsm.addTransition(self.transDict, 'GoodState')
        self.assertEqual(fantasm_tests.MockAction2, transition.action.__class__)

    def test_unresolvedActionYieldsException(self):
        self.transDict[constants.TRANS_ACTION_ATTRIBUTE] = 'VeryBadClass'
        self.assertRaises(exceptions.UnknownClassError, self.fsm.addTransition, self.transDict, 'GoodState')

    def test_unresolvedActionBadClassYieldsException(self):
        self.transDict[constants.NAMESPACE_ATTRIBUTE] = 'bad.namespace'
        self.transDict[constants.TRANS_ACTION_ATTRIBUTE] = 'VeryBadClass'
        self.assertRaises(exceptions.UnknownModuleError, self.fsm.addTransition, self.transDict, 'GoodState')

    def test_invalidAttributeRaisesException(self):
        self.transDict['bad_attribute'] = 'something'
        self.assertRaises(exceptions.InvalidTransitionAttributeError,
                          self.fsm.addTransition, self.transDict, 'GoodState')

    def test_maxRetriesInheritedFromMachine(self):
        transition = self.fsm.addTransition(self.transDict, 'GoodState')
        self.assertEqual(transition.maxRetries, 100)

    def test_queueNameInheritedFromMachine(self):
        transition = self.fsm.addTransition(self.transDict, 'GoodState')
        self.assertEqual(transition.queueName, 'somequeue')

    def test_queueNameOverridesMachineQueueName(self):
        self.transDict[constants.QUEUE_NAME_ATTRIBUTE] = 'someotherqueue'
        transition = self.fsm.addTransition(self.transDict, 'GoodState')
        self.assertEqual(transition.queueName, 'someotherqueue')

    def test_targetInheritedFromMachine(self):
        transition = self.fsm.addTransition(self.transDict, 'GoodState')
        self.assertEqual(transition.target, 'some-target')

    def test_targetOverridesMachineQueueName(self):
        self.transDict[constants.TARGET_ATTRIBUTE] = 'some-other-target'
        transition = self.fsm.addTransition(self.transDict, 'GoodState')
        self.assertEqual(transition.target, 'some-other-target')

    def test_maxRetriesOverridesMachineRetryPolicy(self):
        self.transDict[constants.MAX_RETRIES_ATTRIBUTE] = 99
        transition = self.fsm.addTransition(self.transDict, 'GoodState')
        self.assertEqual(transition.maxRetries, 99)

    def test_maxRetriesEmitsDeprecationWarning(self):
        loggingDouble = getLoggingDouble()
        self.transDict[constants.MAX_RETRIES_ATTRIBUTE] = '3'
        self.fsm.addTransition(self.transDict, 'GoodState')
        self.assertEqual(loggingDouble.count['warning'], 1)

    def test_maxRetriesAndTaskRetryLimitCannotBothBeSpecified(self):
        self.transDict[constants.MAX_RETRIES_ATTRIBUTE] = 99
        self.transDict[constants.TASK_RETRY_LIMIT_ATTRIBUTE] = 99
        self.assertRaises(exceptions.MaxRetriesAndTaskRetryLimitMutuallyExclusiveError,
                          self.fsm.addTransition, self.transDict, 'GoodState')

    def test_settingMaxRetriesSetsTaskRetryLimit(self):
        self.transDict[constants.MAX_RETRIES_ATTRIBUTE] = 99
        transition = self.fsm.addTransition(self.transDict, 'GoodState')
        self.assertEqual(transition.taskRetryLimit, 99)

    def test_settingTaskRetryLimitSetsMaxRetries(self):
        self.transDict[constants.TASK_RETRY_LIMIT_ATTRIBUTE] = 99
        transition = self.fsm.addTransition(self.transDict, 'GoodState')
        self.assertEqual(transition.maxRetries, 99)

    def test_taskRetryLimitInheritedFromMachine(self):
        transition = self.fsm.addTransition(self.transDict, 'GoodState')
        self.assertEqual(transition.taskRetryLimit, 100)

    def test_taskRetryLimitOverridesMachineTaskRetryLimit(self):
        self.transDict[constants.TASK_RETRY_LIMIT_ATTRIBUTE] = 99
        transition = self.fsm.addTransition(self.transDict, 'GoodState')
        self.assertEqual(transition.taskRetryLimit, 99)

    def test_minBackoffSecondsInheritedFromMachine(self):
        transition = self.fsm.addTransition(self.transDict, 'GoodState')
        self.assertEqual(transition.minBackoffSeconds, 101)

    def test_minBackoffSecondsOverridesMachineTaskRetryLimit(self):
        self.transDict[constants.MIN_BACKOFF_SECONDS_ATTRIBUTE] = 99
        transition = self.fsm.addTransition(self.transDict, 'GoodState')
        self.assertEqual(transition.minBackoffSeconds, 99)

    def test_maxBackoffSecondsInheritedFromMachine(self):
        transition = self.fsm.addTransition(self.transDict, 'GoodState')
        self.assertEqual(transition.maxBackoffSeconds, 102)

    def test_maxBackoffSecondsOverridesMachineTaskRetryLimit(self):
        self.transDict[constants.MAX_BACKOFF_SECONDS_ATTRIBUTE] = 99
        transition = self.fsm.addTransition(self.transDict, 'GoodState')
        self.assertEqual(transition.maxBackoffSeconds, 99)

    def test_taskAgeLimitInheritedFromMachine(self):
        transition = self.fsm.addTransition(self.transDict, 'GoodState')
        self.assertEqual(transition.taskAgeLimit, 103)

    def test_taskAgeLimitOverridesMachineTaskRetryLimit(self):
        self.transDict[constants.TASK_AGE_LIMIT_ATTRIBUTE] = 99
        transition = self.fsm.addTransition(self.transDict, 'GoodState')
        self.assertEqual(transition.taskAgeLimit, 99)

    def test_maxDoublingsInheritedFromMachine(self):
        transition = self.fsm.addTransition(self.transDict, 'GoodState')
        self.assertEqual(transition.maxDoublings, 104)

    def test_maxDoublingsOverridesMachineTaskRetryLimit(self):
        self.transDict[constants.MAX_DOUBLINGS_ATTRIBUTE] = 99
        transition = self.fsm.addTransition(self.transDict, 'GoodState')
        self.assertEqual(transition.maxDoublings, 99)

    def test_transitionActionOnContinuationRaisesException(self):
        self.goodState.continuation = True
        self.transDict[constants.TRANS_ACTION_ATTRIBUTE] = 'MockAction'
        self.assertRaises(exceptions.UnsupportedConfigurationError, self.fsm.addTransition, self.transDict, 'GoodState')

    def test_transitionActionOnFanInRaisesException(self):
        self.goodState.fanInPeriod = 10
        self.transDict[constants.TRANS_ACTION_ATTRIBUTE] = 'MockAction'
        self.assertRaises(exceptions.UnsupportedConfigurationError, self.fsm.addTransition, self.transDict, 'GoodState')

    def test_countdownMayNotBeAString(self):
        self.transDict[constants.COUNTDOWN_ATTRIBUTE] = 'abc'
        self.assertRaises(exceptions.InvalidCountdownError, self.fsm.addTransition, self.transDict, 'GoodState')

    def test_countdownMayBeADictionary(self):
        d = {'minimum': 30, 'maximum': 60}
        self.transDict[constants.COUNTDOWN_ATTRIBUTE] = d
        transition = self.fsm.addTransition(self.transDict, 'GoodState')
        self.assertEqual(transition.countdown, (30, 60)) # converted to a tuple

    def test_countdownMustHaveMinimumIfDictionary(self):
        d = {'maximum': 60}
        self.transDict[constants.COUNTDOWN_ATTRIBUTE] = d
        self.assertRaises(exceptions.InvalidCountdownError, self.fsm.addTransition, self.transDict, 'GoodState')

    def test_countdownMustHaveMaximumIfDictionary(self):
        d = {'minimum': 30}
        self.transDict[constants.COUNTDOWN_ATTRIBUTE] = d
        self.assertRaises(exceptions.InvalidCountdownError, self.fsm.addTransition, self.transDict, 'GoodState')

    def test_countdownMustOnlyHaveMinimumAndMaximumIfDictionary(self):
        d = {'minimum': 30, 'maximum': 60, 'other': 90}
        self.transDict[constants.COUNTDOWN_ATTRIBUTE] = d
        self.assertRaises(exceptions.InvalidCountdownError, self.fsm.addTransition, self.transDict, 'GoodState')

    def test_countdownMinimumMustBeInteger(self):
        d = {'minimum': 'abc', 'maximum': 60}
        self.transDict[constants.COUNTDOWN_ATTRIBUTE] = d
        self.assertRaises(exceptions.InvalidCountdownError, self.fsm.addTransition, self.transDict, 'GoodState')

    def test_countdownMaximumMustBeInteger(self):
        d = {'minimum': 30, 'maximum': 'abc'}
        self.transDict[constants.COUNTDOWN_ATTRIBUTE] = d
        self.assertRaises(exceptions.InvalidCountdownError, self.fsm.addTransition, self.transDict, 'GoodState')

    def test_countdownMinimumMustBeNonNegative(self):
        d = {'minimum': -1, 'maximum': 60}
        self.transDict[constants.COUNTDOWN_ATTRIBUTE] = d
        self.assertRaises(exceptions.InvalidCountdownError, self.fsm.addTransition, self.transDict, 'GoodState')

    def test_countdownMaximumMustBeGreaterOrEqualToMinimum(self):
        d = {'minimum': 60, 'maximum': 1}
        self.transDict[constants.COUNTDOWN_ATTRIBUTE] = d
        self.assertRaises(exceptions.InvalidCountdownError, self.fsm.addTransition, self.transDict, 'GoodState')

    def test_countdownParsed(self):
        self.transDict[constants.COUNTDOWN_ATTRIBUTE] = 10
        transition = self.fsm.addTransition(self.transDict, 'GoodState')
        self.assertEqual(transition.countdown, 10)

    def test_countdownInheritedFromMachine(self):
        transition = self.fsm.addTransition(self.transDict, 'GoodState')
        self.assertEqual(transition.countdown, 100)

    def test_countdownOverridesMachineQueueName(self):
        self.transDict[constants.COUNTDOWN_ATTRIBUTE] = 99
        transition = self.fsm.addTransition(self.transDict, 'GoodState')
        self.assertEqual(transition.countdown, 99)

class TestAdvancedTransitionDictionaryProcessing(unittest.TestCase):

    def setUp(self):
        super().setUp()
        self.transDict = {
            constants.TRANS_EVENT_ATTRIBUTE: 'MyEvent',
            constants.TRANS_TO_ATTRIBUTE: 'state2'
        }
        self.fsm = config._MachineConfig({constants.MACHINE_NAME_ATTRIBUTE: 'MyMachine',
                                          constants.NAMESPACE_ATTRIBUTE: 'fantasm_tests.config_test',
                                          constants.TASK_RETRY_LIMIT_ATTRIBUTE: 100})
        self.state1 = self.fsm.addState({constants.STATE_NAME_ATTRIBUTE: 'state1',
                                         constants.STATE_ACTION_ATTRIBUTE: 'MockAction'})
        self.state2 = self.fsm.addState({constants.STATE_NAME_ATTRIBUTE: 'state2',
                                         constants.STATE_ACTION_ATTRIBUTE: 'MockAction'})

    def test_exitActionOnStatesWithTransitionToContinuationRaisesException(self):
        self.state1.exit = 'something-non-null'
        self.state2.continuation = True
        self.assertRaises(exceptions.UnsupportedConfigurationError, self.fsm.addTransition, self.transDict, 'state1')

    def test_exitActionOnStatesWithTransitionToFanInRaisesException(self):
        self.state1.exit = 'something-non-null'
        self.state2.fanInPeriod = 10
        self.assertRaises(exceptions.UnsupportedConfigurationError, self.fsm.addTransition, self.transDict, 'state1')

    def test_transitionActionOnStatesWithTransitionToContinuationRaisesExeption(self):
        self.transDict[constants.TRANS_ACTION_ATTRIBUTE] = 'MockAction'
        self.state2.continuation = True
        self.assertRaises(exceptions.UnsupportedConfigurationError, self.fsm.addTransition, self.transDict, 'state1')

    def test_transitionActionOnStatesWithTransitionToFanInRaisesException(self):
        self.transDict[constants.TRANS_ACTION_ATTRIBUTE] = 'MockAction'
        self.state2.fanInPeriod = 10
        self.assertRaises(exceptions.UnsupportedConfigurationError, self.fsm.addTransition, self.transDict, 'state1')

    def test_countdownOnTransitionToFanInStateRaisesError(self):
        self.transDict[constants.COUNTDOWN_ATTRIBUTE] = 20
        self.state2.fanInPeriod = 10
        self.assertRaises(exceptions.UnsupportedConfigurationError, self.fsm.addTransition, self.transDict, 'state1')

class TestConfigDictionaryProcessing(unittest.TestCase):

    def setUp(self):
        super().setUp()
        self.rootUrl = '/foo/'
        self.machineName = 'MyMachine'
        self.initialStateName = 'MyInitialState'
        self.finalStateName = 'MyState'
        self.baseDict = {
            constants.ROOT_URL_ATTRIBUTE: self.rootUrl,
            constants.STATE_MACHINES_ATTRIBUTE: [
                {
                    constants.MACHINE_NAME_ATTRIBUTE: self.machineName,
                    constants.MACHINE_STATES_ATTRIBUTE: [
                        {
                            constants.STATE_NAME_ATTRIBUTE: self.initialStateName,
                            constants.STATE_ACTION_ATTRIBUTE: 'fantasm_tests.MockAction2',
                            constants.STATE_INITIAL_ATTRIBUTE: True,
                            constants.STATE_FINAL_ATTRIBUTE: False,
                            constants.STATE_TRANSITIONS_ATTRIBUTE: [
                                {
                                    constants.TRANS_EVENT_ATTRIBUTE: 'event1',
                                    constants.TRANS_TO_ATTRIBUTE: self.finalStateName
                                },
                                {
                                    constants.TRANS_EVENT_ATTRIBUTE: 'event2',
                                    constants.TRANS_TO_ATTRIBUTE: self.finalStateName
                                }
                            ]
                        },
                        {
                            constants.STATE_NAME_ATTRIBUTE: self.finalStateName,
                            constants.STATE_ACTION_ATTRIBUTE: 'fantasm_tests.MockAction2',
                            constants.STATE_INITIAL_ATTRIBUTE: False,
                            constants.STATE_FINAL_ATTRIBUTE: True
                        }
                    ]
                }
            ]
        }
        self.myMachineStates = self.baseDict[constants.STATE_MACHINES_ATTRIBUTE][0][constants.MACHINE_STATES_ATTRIBUTE]

    def test_rootUrlPassedToMachines(self):
        configuration = config.Configuration(self.baseDict)
        self.assertEqual(configuration.rootUrl, self.rootUrl)
        self.assertTrue(configuration.machines[self.machineName].url.startswith(self.rootUrl))

    def test_rootUrlHasDefault(self):
        self.baseDict.pop(constants.ROOT_URL_ATTRIBUTE)
        configuration = config.Configuration(self.baseDict)
        self.assertEqual(configuration.rootUrl, constants.DEFAULT_ROOT_URL)

    def test_machinesMustHaveUniqueNames(self):
        self.baseDict[constants.STATE_MACHINES_ATTRIBUTE].append(
            {
                constants.MACHINE_NAME_ATTRIBUTE: self.machineName,
                constants.MACHINE_STATES_ATTRIBUTE: [
                    {
                        constants.STATE_NAME_ATTRIBUTE: self.initialStateName,
                        constants.STATE_ACTION_ATTRIBUTE: 'fantasm_tests.MockAction2',
                        constants.STATE_INITIAL_ATTRIBUTE: True,
                        constants.STATE_FINAL_ATTRIBUTE: True
                    }
                ]
            }
        )
        self.assertRaises(exceptions.MachineNameNotUniqueError, config.Configuration, self.baseDict)

    def test_multipleMachinesParsed(self):
        otherMachineName = 'OtherMachine'
        self.baseDict[constants.STATE_MACHINES_ATTRIBUTE].append(
            {
                constants.MACHINE_NAME_ATTRIBUTE: otherMachineName,
                constants.MACHINE_STATES_ATTRIBUTE: [
                    {
                        constants.STATE_NAME_ATTRIBUTE: self.initialStateName,
                        constants.STATE_ACTION_ATTRIBUTE: 'fantasm_tests.MockAction2',
                        constants.STATE_INITIAL_ATTRIBUTE: True,
                        constants.STATE_FINAL_ATTRIBUTE: True
                    }
                ]
            }
        )
        configuration = config.Configuration(self.baseDict)
        self.assertEqual(configuration.machines[self.machineName].name, self.machineName)
        self.assertEqual(configuration.machines[otherMachineName].name, otherMachineName)

    def test_statesAddedToMachines(self):
        configuration = config.Configuration(self.baseDict)
        myMachine = configuration.machines[self.machineName]
        self.assertEqual(len(myMachine.states), 2)
        self.assertEqual(myMachine.states[self.initialStateName].name, self.initialStateName)
        self.assertEqual(myMachine.states[self.finalStateName].name, self.finalStateName)

    def test_machineWithNoInitialRaisesException(self):
        # this is hairy, but I'm going to clear the initial flag on the state
        self.myMachineStates[0][constants.STATE_INITIAL_ATTRIBUTE] = False # updates self.baseDict
        self.assertRaises(exceptions.MachineHasNoInitialStateError, config.Configuration, self.baseDict)

    def test_machineWithMultipleInitialRaisesException(self):
        # here, I'm going to set the initial flag on the second, non-initial state
        self.myMachineStates[1][constants.STATE_INITIAL_ATTRIBUTE] = True # updates self.baseDict
        self.assertRaises(exceptions.MachineHasMultipleInitialStatesError,
                          config.Configuration, self.baseDict)

    def test_machineWithNoFinalRaisesException(self):
        # here, I'm going to clear the final flag on the second state, which is the only final state
        self.myMachineStates[1][constants.STATE_FINAL_ATTRIBUTE] = False # updates self.baseDict
        self.assertRaises(exceptions.MachineHasNoFinalStateError, config.Configuration, self.baseDict)

    def test_transitionsAddedToMachines(self):
        configuration = config.Configuration(self.baseDict)
        myMachine = configuration.machines[self.machineName]
        self.assertEqual(len(myMachine.transitions), 2)
        trans1Name = self.initialStateName + '--event1'
        trans2Name = self.initialStateName + '--event2'
        self.assertEqual(myMachine.transitions[trans1Name].name, trans1Name)
        self.assertEqual(myMachine.transitions[trans2Name].name, trans2Name)

    def test_stateMachineAttributeRequired(self):
        self.assertRaises(exceptions.StateMachinesAttributeRequiredError, config.Configuration, {})

    def test_builtInMachinesImported(self):
        configuration = config.Configuration(self.baseDict)
        self.assertTrue('FantasmScrubber' in configuration.machines)
        self.assertTrue('init' in configuration.machines['FantasmScrubber'].states)

class TestYamlFileLocation(unittest.TestCase):

    def test_noYamlFileRaisesException(self):
        self.assertRaises(exceptions.YamlFileNotFoundError, config.loadYaml, filename='nofile.yaml')

    def test_yamlFileFound(self):
        import os
        filename = os.path.join(os.path.dirname(__file__), 'yaml', 'test-TestYamlFileLocation.yaml')
        configuration = config.loadYaml(filename=filename)
        self.assertTrue('MyMachine' in configuration.machines)

NAMESPACED_EVENT_MODULE_LEVEL = 'NAMESPACED-EVENT-MODULE-LEVEL'
NAMESPACED_CONTEXT_TYPE_MODULE_LEVEL = 'NAMESPACED-CONTEXT-TYPE-MODULE-LEVEL'

class TestNamespacedEventsAndContextTypes(unittest.TestCase):

    NAMESPACED_EVENT_CLASS_LEVEL = 'NAMESPACED-EVENT-CLASS-LEVEL'
    NAMESPACED_CONTEXT_TYPE_CLASS_LEVEL = 'NAMESPACED-CONTEXT-TYPE-CLASS-LEVEL'

    def _test(self, yamlString):
        """ just tests that it can be built """
        import io, yaml
        yamlFile = io.StringIO()
        yamlFile.write(yamlString)
        yamlFile.seek(0)
        configDict = yaml.load(yamlFile.read())
        configuration = config.Configuration(configDict)
        return configuration

    def test_module_level(self):
        configuration = self._test(
"""
state_machines:
- name: machineName
  namespace: fantasm_tests.config_test
  context_types:
    NAMESPACED_CONTEXT_TYPE_MODULE_LEVEL: int
  states:
    - name: state1
      action: fantasm_tests.fsm_test.CountExecuteCalls
      initial: True
      transitions:
      - event: NAMESPACED_EVENT_MODULE_LEVEL
        to: state2
    - name: state2
      final: True
""")
        self.assertEqual(
            'NAMESPACED-EVENT-MODULE-LEVEL',
            configuration.machines['machineName'].transitions['state1--NAMESPACED-EVENT-MODULE-LEVEL'].event
        )
        self.assertEqual(
            {'NAMESPACED-CONTEXT-TYPE-MODULE-LEVEL': int},
            configuration.machines['machineName'].contextTypes
        )

    def test_module_level_other(self):
        configuration = self._test(
"""
state_machines:
- name: machineName
  namespace: fantasm_tests.config_test
  context_types:
    fantasm_tests.fsm_test.NAMESPACED_CONTEXT_TYPE_MODULE_LEVEL_FSM_TESTS: int
  states:
    - name: state1
      action: fantasm_tests.fsm_test.CountExecuteCalls
      initial: True
      transitions:
      - event: fantasm_tests.fsm_test.NAMESPACED_EVENT_MODULE_LEVEL_FSM_TESTS
        to: state2
    - name: state2
      final: True
""")
        self.assertEqual(
            'NAMESPACED-EVENT-MODULE-LEVEL-FSM-TESTS',
            configuration.machines['machineName'].transitions['state1--NAMESPACED-EVENT-MODULE-LEVEL-FSM-TESTS'].event
        )
        self.assertEqual(
            {'NAMESPACED-CONTEXT-TYPE-MODULE-LEVEL-FSM-TESTS': int},
            configuration.machines['machineName'].contextTypes
        )

    def test_class_level(self):
        configuration = self._test(
"""
state_machines:
- name: machineName
  namespace: fantasm_tests.config_test
  context_types:
    TestNamespacedEventsAndContextTypes.NAMESPACED_CONTEXT_TYPE_CLASS_LEVEL: int
  states:
    - name: state1
      action: fantasm_tests.fsm_test.CountExecuteCalls
      initial: True
      transitions:
      - event: TestNamespacedEventsAndContextTypes.NAMESPACED_EVENT_CLASS_LEVEL
        to: state2
    - name: state2
      final: True
""")
        self.assertEqual(
            'NAMESPACED-EVENT-CLASS-LEVEL',
            configuration.machines['machineName'].transitions['state1--NAMESPACED-EVENT-CLASS-LEVEL'].event
        )
        self.assertEqual(
            {'NAMESPACED-CONTEXT-TYPE-CLASS-LEVEL': int},
            configuration.machines['machineName'].contextTypes
        )

    def test_class_level_other(self):
        configuration = self._test(
"""
state_machines:
- name: machineName
  namespace: fantasm_tests.config_test
  context_types:
    fantasm_tests.fsm_test.FSMTests.NAMESPACED_CONTEXT_TYPE_CLASS_LEVEL_FSM_TESTS: int
  states:
    - name: state1
      action: fantasm_tests.fsm_test.CountExecuteCalls
      initial: True
      transitions:
      - event: fantasm_tests.fsm_test.FSMTests.NAMESPACED_EVENT_CLASS_LEVEL_FSM_TESTS
        to: state2
    - name: state2
      final: True
""")
        self.assertEqual(
            'NAMESPACED-EVENT-CLASS-LEVEL-FSM-TESTS',
            configuration.machines['machineName'].transitions['state1--NAMESPACED-EVENT-CLASS-LEVEL-FSM-TESTS'].event
        )
        self.assertEqual(
            {'NAMESPACED-CONTEXT-TYPE-CLASS-LEVEL-FSM-TESTS': int},
            configuration.machines['machineName'].contextTypes
        )

    def test_just_a_plain_old_string(self):
        configuration = self._test(
"""
state_machines:
- name: machineName
  namespace: fantasm_tests.config_test
  context_types:
    fantasm_tests.fsm_test.FSMTests.NAMESPACED_CONTEXT_TYPE_CLASS_LEVEL_FSM_TESTS: int
    abc: long
  states:
    - name: state1
      action: fantasm_tests.fsm_test.CountExecuteCalls
      initial: True
      transitions:
      - event: just-a-plain-old-string
        to: state2
    - name: state2
      final: True
""")
        self.assertEqual(
            'just-a-plain-old-string',
            configuration.machines['machineName'].transitions['state1--just-a-plain-old-string'].event
        )
        self.assertEqual(
            {'NAMESPACED-CONTEXT-TYPE-CLASS-LEVEL-FSM-TESTS': int, 'abc': int},
            configuration.machines['machineName'].contextTypes
        )


    WRONG_TYPE = 999

    def test_wrong_type(self):
        self.assertRaises(exceptions.UnexpectedObjectTypeError, self._test,
"""
state_machines:
- name: machineName
  namespace: fantasm_tests.config_test
  states:
    - name: state1
      action: fantasm_tests.fsm_test.CountExecuteCalls
      initial: True
      transitions:
      - event: TestNamespacedEventsAndContextTypes.WRONG_TYPE
        to: state2
    - name: state2
      final: True
""")

    def test_wrong_type_context_type(self):
        self.assertRaises(exceptions.UnexpectedObjectTypeError, self._test,
"""
state_machines:
- name: machineName
  namespace: fantasm_tests.config_test
  context_types:
     TestNamespacedEventsAndContextTypes.WRONG_TYPE: int
  states:
    - name: state1
      action: fantasm_tests.fsm_test.CountExecuteCalls
      initial: True
      transitions:
      - event: event
        to: state2
    - name: state2
      final: True
""")

class TestStatesWithAndWithoutDoActions(unittest.TestCase):

    def _test(self, yamlString):
        """ just tests that it can be built """
        import io, yaml
        yamlFile = io.StringIO()
        yamlFile.write(yamlString)
        yamlFile.seek(0)
        configDict = yaml.load(yamlFile.read())
        configuration = config.Configuration(configDict)
        self.assertTrue(configuration)

    def test_finalStateWithDoAction(self):
        self._test(
"""
state_machines:
- name: machineName
  namespace: fantasm_tests.fsm_test
  states:
    - name: state1
      entry: CountExecuteCalls
      action: CountExecuteCalls
      exit: CountExecuteCalls
      initial: True
      final: True
""")

    def test_finalStateWithOutDoAction(self):
        self._test(
"""
state_machines:
- name: machineName
  namespace: fantasm_tests.fsm_test
  states:
    - name: state1
      entry: CountExecuteCalls
      exit: CountExecuteCalls
      initial: True
      final: True
""")

    def test_nonFinalStateWithOutDoAction(self):
        self.assertRaises(exceptions.StateActionRequired, self._test,
"""
state_machines:
- name: machineName
  namespace: fantasm_tests.fsm_test
  states:
    - name: state1
      entry: CountExecuteCalls
      exit: CountExecuteCalls
      initial: True
""")

# class TestMachineConfigRetrieval(unittest.TestCase):
#
#     def test_ensureMachineConfigIsCachedStatically(self):
#         pass # TODO
#
#     def test_ensureYamlFileUpdateClearsStaticCache(self):
#         pass # TODO
