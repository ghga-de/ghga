# Notification Service Update (Scissor Grinder Cicada)
**Epic Type:** Implementation Epic

## Scope:
This epic will add a SMS channel to Notification Service to enable SMS delivery.
It will include:
- Schema definition for a SMS notification event
- Adding the schema to ghga-event-schemas
- Functionality for consuming those events and dispatching notifications via a SMS gateway

It does not include:
- Changing existing services to send SMS notification events
- Update Notification Orchestration Service to emit SMS notification events

## Additional Implementation Details:

### SMS Notification Event
A SMS Notification event schema will be defined in the ghga-event-schemas repository.
The event schema will detail all the information needed to send a notification via SMS:
- text (required)
- phone (required)
- delivery_at (optional)
The exact field names and constraints will be provided in the ghga-event-schemas repository, which is considered the source of truth.
This information will be used to create a SMS with a consistent format.

### Notification Service
This is a microservice dedicated to consuming Notification events from the "notifications" topic in kafka.
In this update a new type of notification event will be added to expand the service's capabilities.
In order to utilize the notification service to send SMS, publishers will need to publish an event to the "notifications" topic using the "SMS notification" event type, with a payload conforming to the schema defined by SmsNotification in the ghga-event-schemas repository.
SMS will be sent via HTTP and SMS contents will be injected into the requests. The parameters required to successfully configure the service are as follows:
- sms_gateway_address: The address of the SMS gateway
- sms_gateway_port: The port to use
- token: The API token used for authentication and authorization
- sender_id: Sender's id or phone number

## Human Resource/Time Estimation:

Number of sprints required: 1

Number of developers required: 1
