import json

from django.test import TestCase, Client, RequestFactory

# Create your tests here.
from django.urls import reverse
from django.utils import timezone


class SQSLocaltestCase(TestCase):

    def setUp(self):
        pass

    def test_local_echo_task_sending(self):
        with self.settings(
                AWS_EB_HANDLE_SQS_TASKS=False,  # must be True ONLY on isolated worker environments
                AWS_EB_RUN_TASKS_LOCALLY=True,  # set to False to send tasks to SQS
                AWS_EB_ENABLED_TASKS={
                    "echo_task": "eb_sqs.tasks.test_task"
                }
        ):
            from eb_sqs import sqs
            sqs.send_task("echo_task", {"foo": "bar"})

    def test_cant_send_task_of_handle_sqs_disabled(self):
        with self.settings(
                AWS_EB_HANDLE_SQS_TASKS=False,  # must be True ONLY on isolated worker environments
                AWS_EB_RUN_TASKS_LOCALLY=True,  # set to False to send tasks to SQS
                AWS_EB_ENABLED_TASKS={
                    "echo_task": "eb_sqs.tasks.test_task"
                }
        ):
            response = self.client.post(reverse("sqs_handle"),
                                        data={
                                            "task": "foo",
                                            "arguments": "bar"
                                        })

            self.assertEqual(response.status_code, 404)

    def test_wrong_user_agent_rejected_from_posting_tasks(self):
        with self.settings(
                AWS_EB_HANDLE_SQS_TASKS=True,  # must be True ONLY on isolated worker environments
                AWS_EB_RUN_TASKS_LOCALLY=False,  # set to False to send tasks to SQS
                AWS_EB_ENABLED_TASKS={
                    "echo_task": "eb_sqs.tasks.test_task"
                }
        ):
            response = self.client.post(reverse("sqs_handle"),
                                       json.dumps({
                                           "task": "echo_task",
                                           "arguments": {"foo":"bar"}
                                       }), content_type="application/json")

            self.assertEqual(response.status_code, 400)

    def test_handle_task_if_sqs_enabled(self):
        with self.settings(
                AWS_EB_HANDLE_SQS_TASKS=True,  # must be True ONLY on isolated worker environments
                AWS_EB_RUN_TASKS_LOCALLY=False,  # set to False to send tasks to SQS
                AWS_EB_ENABLED_TASKS={
                    "echo_task": "eb_sqs.tasks.test_task"
                }
        ):
            # add correct user-agent see https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/using-features
            # -managing-env-tiers.html#worker-daemon

            sqs_client = Client(HTTP_USER_AGENT="aws-sqsd/1.1")
            response = sqs_client.post(reverse("sqs_handle"),
                                       json.dumps({
                                           "task": "echo_task",
                                           "arguments": {"foo":"bar"}
                                       }), content_type="application/json")

            self.assertEqual(response.status_code, 200)


class SQSLocalPeriodicTaskTestCase(TestCase):

    def test_local_periodic_echo_task_sending(self):
        with self.settings(
                AWS_EB_HANDLE_SQS_TASKS=True,  # must be True ONLY on isolated worker environments
                AWS_EB_RUN_TASKS_LOCALLY=True,  # set to False to send tasks to SQS
                AWS_EB_ENABLED_TASKS={
                    "echo_task": "eb_sqs.tasks.test_task"
                }
        ):
            from eb_sqs import sqs

            factory = RequestFactory()

            sqs_client = Client(HTTP_USER_AGENT="aws-sqsd/1.1")
            response = sqs_client.post(reverse("sqs_handle"),
                                       # no body
                                       # should work without json content-type
                                       # content_type="application/json",
                                       # headers
                                       **{
                                           "HTTP_X-Aws-Sqsd-Taskname": "echo_task",
                                           "HTTP_X-Aws-Sqsd-Scheduled-At": timezone.now().isoformat(),
                                           "HTTP_X-Aws-Sqsd-Sender-Id": "test-id"
                                       })

            self.assertEqual(response.status_code, 200)