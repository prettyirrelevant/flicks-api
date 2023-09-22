from django.test import TestCase

from rest_framework.test import APIClient

from apps.webhooks.models import Webhook

CONFIRM_SUBSCRIPTION_PAYLOAD = r"""{
  "Type" : "SubscriptionConfirmation",
  "MessageId" : "104b659d-9507-4716-aba6-85255966856d",
  "Token" : "2336412f37fb687f5d51e6e2425c464dec3a56535a504fc27104a2f2c15f44b35827a34f8e4bb233b40799e3584e21022f4d7f27a04f729f92cc81b813f20544ccea7c81a3ee335cbb08c9bfcfb15e26a3d0cdb50d9bb4d12b0625f703985b74c6e4102ce0fc177468a8a5a13873d9e7a3b551a3667920afa1ce97905f04a99e2b5913b31548d5e66e93b669b247334d",
  "TopicArn" : "arn:aws:sns:us-east-1:908968368384:sandbox_platform-notifications-topic",
  "Message" : "You have chosen to subscribe to the topic arn:aws:sns:us-east-1:908968368384:sandbox_platform-notifications-topic.\nTo confirm the subscription, visit the SubscribeURL included in this message.",
  "SubscribeURL" : "https://sns.us-east-1.amazonaws.com/?Action=ConfirmSubscription&TopicArn=arn:aws:sns:us-east-1:908968368384:sandbox_platform-notifications-topic&Token=2336412f37fb687f5d51e6e2425c464dec3a56535a504fc27104a2f2c15f44b35827a34f8e4bb233b40799e3584e21022f4d7f27a04f729f92cc81b813f20544ccea7c81a3ee335cbb08c9bfcfb15e26a3d0cdb50d9bb4d12b0625f703985b74c6e4102ce0fc177468a8a5a13873d9e7a3b551a3667920afa1ce97905f04a99e2b5913b31548d5e66e93b669b247334d",
  "Timestamp" : "2023-09-20T16:31:53.633Z",
  "SignatureVersion" : "1",
  "Signature" : "VVMhCkA/ut3waEt2IKuPhzYFMPkXExtz6nXN/ae2w4wAv9L1lclMlHYEOnbJXkMUUra4zOZvQTcJ5SruG7clAYm63HT90LoKL1oAAGIisHppyd4KbLCEr6sB5oR+Wgp/0i9G+Y5VnUStjx6SyRPZjWBEITHKvjlM2Nmx+ZcsmWB7//wXK4lY/VxAY8FX7wiOPUB5vYS3nUDQZvxsGRO0f3jV+V+aCTye52FD5aVJYk4f4Eh54RRNSkgeYROZ2rZWVGNPu55lDnuV9qh+v2ja2gQk6Y7LjtVtHg0f79FBjNpHqZDl/24I19KAbR0PaKomx1xrZh7ojBKXR7wb7dmjVg==",
  "SigningCertURL" : "https://sns.us-east-1.amazonaws.com/SimpleNotificationService-01d088a6f77103d0fe307c0069e40ed6.pem"
}"""  # noqa: E501

TRANSFER_RECEIVED_PAYLOAD = r"""{
  "Type" : "Notification",
  "MessageId" : "49e77e2a-3dcd-5d40-a42b-23af199310a0",
  "TopicArn" : "arn:aws:sns:us-east-1:908968368384:sandbox_platform-notifications-topic",
  "Message" : "{\"clientId\":\"6c2bcca2-9ee9-426f-8691-25cba95f5085\",\"notificationType\":\"transfers\",\"version\":1,\"customAttributes\":{\"clientId\":\"6c2bcca2-9ee9-426f-8691-25cba95f5085\"},\"transfer\":{\"id\":\"317c3ae9-79e2-3c9a-a14c-f341cfebf780\",\"source\":{\"type\":\"blockchain\",\"chain\":\"MATIC\"},\"destination\":{\"type\":\"wallet\",\"id\":\"1016606173\",\"address\":\"0xfe0fe6cac9e34337e499c1d92c3bb3ef83a62dab\"},\"amount\":{\"amount\":\"10.00\",\"currency\":\"USD\"},\"transactionHash\":\"0xa2a909eed30469478da7a4a3a84e9456e42e5b8b2a2545446b3c63c30ed5989a\",\"status\":\"complete\",\"createDate\":\"2023-09-20T16:42:09.595Z\"}}",
  "Timestamp" : "2023-09-20T16:47:26.916Z",
  "SignatureVersion" : "1",
  "Signature" : "XY1vOp0WEfUI4FI4IuD9fbZQWKGrw79cVbgdbUNrqLFC5EhQYVL8kp1ogfHvZeI0nyDyFrtbNsDmeTaWFzXGSthVGHZkUeVN5cZLr6SvHiL1AGr6YCMbpnRDIXO7n1yXvXZuLmQk5qgBs3yiNmd41+g59x3Zzm3PCjgUZjVw098B5O2rZNOrcG2XTvxVWVL4V4Zchqp/SonM9neuae/f/BdcaCR1hrO7c31Pmavl3WKkyf3mSkl/7DuvX22N/aw5SxbzVqksip21+cfy+pQmagv8hxqIP/BnZQAZgEkGTA6qON+7fWpPtcmM4/7DzUZRV6wBu6Q220USZ3Ohpb6Uew==",
  "SigningCertURL" : "https://sns.us-east-1.amazonaws.com/SimpleNotificationService-01d088a6f77103d0fe307c0069e40ed6.pem",
  "UnsubscribeURL" : "https://sns.us-east-1.amazonaws.com/?Action=Unsubscribe&SubscriptionArn=arn:aws:sns:us-east-1:908968368384:sandbox_platform-notifications-topic:06f0aea9-484d-42fe-a1f2-476dc33c6059",
  "MessageAttributes" : {
    "clientId" : {"Type":"String","Value":"6c2bcca2-9ee9-426f-8691-25cba95f5085"}
  }
}"""  # noqa: E501


class WebhookTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_webhook_endpoint_confirm_subscription(self):
        response = self.client.post(
            path='/api/webhooks',
            data=CONFIRM_SUBSCRIPTION_PAYLOAD,
            content_type='text/plain; charset=utf-8',
            headers={'x-amz-sns-message-type': 'SubscriptionConfirmation'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Webhook.objects.count(), 1)

    def test_webhook_endpoint_transfer_received(self):
        response = self.client.post(
            path='/api/webhooks',
            data=TRANSFER_RECEIVED_PAYLOAD,
            content_type='text/plain; charset=utf-8',
            headers={'x-amz-sns-message-type': 'SubscriptionConfirmation'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Webhook.objects.count(), 1)
