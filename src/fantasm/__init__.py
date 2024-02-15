""" Fantasm: A taskqueue-based Finite State Machine for App Engine Python

Docs and examples: http://code.google.com/p/fantasm/

Copyright 2010 VendAsta Technologies Inc.

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.

Release Notes:

v2.0.0
- Python 3 migration
    - dropped support for Python 2
    - dropped support for outputting graphviz visualizations
    - webapp2 is not supported in Python 3, so you install fantasm via wrap_wsgi_app. Flask example:
        app = Flask(__name__)
        app.wsgi_app = fantasm.wrap_wsgi_app(app.wsgi_app)

v1.3.4
- minor change to pylint formatting

v1.3.3
- added exception handling around failures in capabilities check; if there is a failure in the
  capabilities check, we will just assume things are okay and continue on

v1.3.2
- added hook in NDBDatastoreContinuationFSMAction allowing the query's read consistency to be set

v1.3.1
- added context.getInstanceStartTime(), which returns a datetime object with the UTC datetime
  when the instance was started

v1.3.0
- allow countdown on transition to accept a minimum/maximum value; the countdown will be chosen
  randomly between these two ranges, e.g.,

      transitions:
        - event: next
          to: next-state
          action: MyAction
          countdown:
            minimum: 30
            maximum: 60

v1.2.1
- fixed bug related to default serialization of ndb.Key on fan-in states

v1.2.0
- allow the capabilities check to be configured with "enable_capabilties_check" in fantasm.yaml (default True)
- fixed https://code.google.com/p/fantasm/issues/detail?id=8
- fixes https://code.google.com/p/fantasm/issues/detail?id=10

v1.1.1
- very minor bug fix

v1.1.0
- added fantasm.exceptions.HaltMachineError; when raised the machine will be stopped without needing
  to specify "final: True" on the state. Normally if a None event is returned from a "final: False"
  state, Fantasm complains loudly. HaltMachineError provides a way to kill a machine without this
  loud complaint in the logs, though the HaltMachineError allows you to provide a log message and
  a log level to log at (logLevel=None means do not emit a message at all).

v1.0.1
- fixed an issue with context.setQueue()

v1.0.0
- we've been out for a long time, but never had formal release notes. Gotta start somewhere!

"""

__version__ = '2.0.0'

from fantasm import console
from fantasm import handlers

# W0401:  2: Wildcard import fsm
# pylint: disable-msg=W0401
from fantasm.fsm import *


def wrap_wsgi_app(app):
    """ 
    Wrap the given WSGI app with the fantasm middleware. 
    
    Example:
    app = Flask(__name__)
    app.wsgi_app = fantasm.wrap_wsgi_app(app.wsgi_app)

    Make sure that this is done BEFORE adding the appengine WSGI middleware:

    from google.appengine.api import wrap_wsgi_app
    ...
    app.wsgi_app = fantasm.wrap_wsgi_app(app.wsgi_app)
    app.wsgi_app = wrap_wsgi_app(app.wsgi_app, use_legacy_context_mode=True, use_deferred=True)
    """
    return lambda wsgi_env, start_response: FantasmMiddleware(app, wsgi_env, start_response)


def FantasmMiddleware(app, wsgi_env, start_response):
    """ Add the fantasm middleware to the given WSGI app. """
    path = wsgi_env['PATH_INFO']
    if path.startswith('/fantasm/'):
        routes = {
            'fsm': handlers.FSMHandler,
            'cleanup': handlers.FSMFanInCleanupHandler,
            'log': handlers.FSMLogHandler,
        }
        path_segment = path.split('/')[2]
        handler = routes.get(path_segment)
        if handler:
            return handler()(wsgi_env, start_response)
        return console.Dashboard()(wsgi_env, start_response)
    return app(wsgi_env, start_response)

