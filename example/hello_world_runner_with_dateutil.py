from wca.runners import Runner
from dateutil.utils import today


class HelloWorldRunner(Runner):

    def run(self):
        print('Hello world! Today is %s' % today())
