The Notification Service is a microservice intended to provide general notification capabilities. At this time, notifications are only generated via Kafka events, and they are only issued via email.
However, the architecture of the service would allow for the addition of other submission options, such as REST APIs, as well as new notification channels, such as SMS, with relatively little work.

To send an email notification using this service, publish a kafka event conforming to the Notification event schema to the topic configured under "notification_event_topic" (see configuration details below). Because email client authentication is handled by the notification service itself, nothing beyond publishing the event is required.


### Typical operation

This service doesn't have a REST API. It is fully stateless and does not require a database.
It's a straightforward service running a Kafka consumer that listens for one kind of event.
Notification events are picked up by the consumer, validated against the Notification event schema, and sent to the Notifier module.
The Notifier looks at the notification event details and determines what to do with it.
Right now, this always means sending an email.
The information is sent to the SMTP client, where a secure connection is established and the email is dispatched.

### Email Templates

In the configuration there are two template requirements: a plaintext email template and an HTML email template. The point of these is to produce consistently formatted emails while keeping the requirements light for microservices trying to send notifications. The templates are both used to make the email. Template variables are denoted with "$", e.g. $recipient_name, and are required to match the notification schema field names defined [here](https://github.com/ghga-de/ghga-event-schemas/blob/8e535ac271e7f27b6132505aad8cf572decc7ab4/ghga_event_schemas/pydantic_.py#L304). Having both HTML and plaintext means everyone should be able to receive the emails without a problem, and most of the time they should look nice. Because email clients like Outlook, Gmail, etc. have differences in the way they render HTML emails, it is recommended that styling be kept to a minimum or to use a pre-made template where these things have been taken into account.
