""" Webapp main module """

import uuid
import logging
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import webapp
from google.appengine.ext import db
from .complex_machine import TestModel
from . import email_batch
from . import backup

# pylint: disable=C0111, C0103
# - docstring not reqd
# - application in lower case is acceptable

class HomePage(webapp.RequestHandler):

    def get(self):

        self.response.out.write("""
<html>
<head><title>Fantasm example</title></head>

<body>

<h1>Fantasm Examples</h1>

<p>These examples have no output in HTML. Instead, you need to look at your log file and (for some tests), your
datasore to see the results.</p>

<h2>1. Simple Machine</h2>
<p>This machine has a simple set of states and just moves through them. A log line is emitted for each event.</p>
<p>Click <a href="/fantasm/graphviz/SimpleMachine/">/fantasm/graphviz/SimpleMachine/</a> to view a GraphViz diagram of the machine.</p>
<p>Click <a href="/fantasm/fsm/SimpleMachine/">/fantasm/fsm/SimpleMachine/</a> to kick a simple workflow off.</p>
<p>Click <a href="/fantasm/fsm/SimpleMachine/?failure=1">/fantasm/fsm/SimpleMachine/?failure=1</a> to kick a simple workflow off
with randomly injected exceptions.</p>

<h2>2. Fan-out Example</h2>
<p>
This machine fans out multiple machine instances. Each instance grabs a page of results from a Twitter search
and stores them in datastore. This machine has only a single state (that is a "continuation" state).
</p>
<p>Click <a href="/fantasm/graphviz/UrlFanoutExample/">/fantasm/graphviz/UrlFanoutExample/</a> to view a GraphViz diagram of the machine.</p>
<p>Click <a href="/fantasm/fsm/UrlFanoutExample/">/fantasm/fsm/UrlFanoutExample/</a>
   to kick a continuation workflow off.</p>

<h2>3. Fan-out / Fan-in Example</h2>
<p>
This machine fans-out a new instance to send an email to each in a list of subscribers. The instances are then
fanned-in on a 30 second interval to increment the count of number of emails sent.
</p>
<p>First, click <a href="/create-subscribers/">/create-subscribers/</a> to create test subscribers.</p>
<p>Click <a href="/fantasm/graphviz/EmailBatch/">/fantasm/graphviz/EmailBatch/</a> to view a GraphViz diagram of the machine.</p>
<p>Click <a href="/fantasm/fsm/EmailBatch/">/fantasm/fsm/EmailBatch/</a> to kick an example email batch (fan-out / fan-in, no emails sent).</p>

<h2>4. Complex Machine</h2>
<p>
A more complex machine that we use for testing some advanced interactions.
</p>
<p>First, click <a href="/MakeAModel/">/MakeAModel/</a> to create a TestModel.</p>
<p>Click <a href="/fantasm/graphviz/ComplexMachine/">/fantasm/graphviz/ComplexMachine/</a> to view a GraphViz diagram of the machine.</p>
<p>Click <a href="/fantasm/fsm/ComplexMachine/">/fantasm/fsm/ComplexMachine/</a> to kick a workflow off.</p>
<p>Click <a href="/fantasm/fsm/ComplexMachine/?failure=1">/fantasm/fsm/ComplexMachine/?failure=1</a> to kick a workflow off
with randomly injected exceptions.</p>

<h2>5. Incremental Backup</h2>
<p>
A Fantasm-based mechanism to backup data incrementally to an alternate datastore namespace. Also includes
a machine to scrub out aged backups.
</p>
<p>First, click <a href='/backup/populate/'>/backup/populate/</a> to create some test data.</p>
<p>Click <a href='/fantasm/fsm/Backup/'>/fantasm/fsm/Backup/</a> to start the backup.</p>
<p>In the console, look at _Backup model to see what backupId was created. This is the name of the datastore namespace
where the data is backed up.</p>
<p>Also, look at the backup queue. You will see a task queued into the future; this is the delete aged backups task.
You can go ahead and delete it, we'll invoke it manually below.</p>
</p>Click <a href='/backup/populate/'>/backup/populate/</a> again to create some new data and overwrite existing data.</p>
<p>Click <a href='/fantasm/fsm/Backup/'>/fantasm/fsm/Backup/</a> to start the incremental backup. Only new data will be
backed up.</p>
<p>Click <a href='/fantasm/fsm/DeleteBackup/?daysOld=0'>/fantasm/fsm/DeleteBackup/?daysOld=0</a> to kick off
a delete aged backups job. daysOld=0 means delete the most recent backups. This will remove the entries from _Backup as
well as the corresponding backup entities in the corresponding datastore namespaces.</a>


</body>
</html>
""")

class MakeAModel(webapp.RequestHandler):

    def get(self):
        TestModel(prop1=str(uuid.uuid4())).put()

class Make100Models(webapp.RequestHandler):

    def get(self):
        models = []
        for i in range(100): # pylint: disable=W0612
            models.append(TestModel(prop1=str(uuid.uuid4())))
        db.put(models)

class Start100ComplexMachine(webapp.RequestHandler):

    def get(self):
        from . import fantasm
        fantasm.fsm.startStateMachine('ComplexMachine', [{}] * 100)

class SecurityToken(db.Model):
    """ An uber-simple security check for views. """
    name = db.StringProperty(required=True)
    token = db.StringProperty(required=True)

def checkSecurity(name, request):
    """ Returns true if the security check succeeds, false otherwise. """
    token = request.params.get('token')
    securityToken = SecurityToken.get_by_key_name(name)
    if not securityToken:
        return False
    if securityToken.token != token:
        return False
    return True

class Start100ComplexMachineCountdown(webapp.RequestHandler):

    def get(self):
        from . import fantasm
        fantasm.fsm.startStateMachine('ComplexMachine', [{}] * 100, countdown=[i*300 for i in range(100)])

class IntegrationTest(webapp.RequestHandler):

    def get(self):

        # security check
        if not checkSecurity('integration-test', self.request):
            self.response.set_status(401)
            return

        from . import fantasm
        for _ in range(10):
            fantasm.fsm.startStateMachine('ComplexMachine', [{}] * 100, countdown=[i*300 for i in range(100)])

class NDBIntegrationTest(webapp.RequestHandler):

    def get(self):

        # security check
        if not checkSecurity('integration-test', self.request):
            self.response.set_status(401)
            return

        from . import fantasm
        for _ in range(10):
            fantasm.fsm.startStateMachine('NDBComplexMachine', [{}] * 100, countdown=[i*300 for i in range(100)])

class IntegrationTestResults(webapp.RequestHandler):

    def get(self):

        # security check
        if not checkSecurity('integration-test-results', self.request):
            self.response.set_status(401)
            return

        #
        # Work in progress
        #
        # check default queue and fan_in queue; if non-zero, return notdone
        # query ResultsModel for items != 1000
        #   version = os.environ['CURRENT_VERSION_ID'].split('.')[0]
        #   SELECT * FROM ResultsModel where version=version and total != 1000
        # return
        #    10 (undercount)
        #     3 (overcount)
        # *** The resulting file needs to integrate with integration-test-results target in build.xml
        return

application = webapp.WSGIApplication([
    ('/', HomePage),
    ('/MakeAModel/', MakeAModel),
    ('/Make100Models/', Make100Models),
    ('/Start100ComplexMachine/', Start100ComplexMachine),
    ('/Start100ComplexMachineCountdown/', Start100ComplexMachineCountdown),
    ('/integration-test/', IntegrationTest),
    ('/ndb-integration-test/', NDBIntegrationTest),
    ('/integration-test-results/', IntegrationTestResults),
    ('/create-subscribers/', email_batch.CreateSubscribers),
    ('/backup/populate/', backup.PopulateBackupExample)
], debug=True)

def main():
    logging.getLogger().setLevel(logging.DEBUG)
    run_wsgi_app(application)

if __name__ == "__main__":
    main()

