# Notification Service Update (Scissor Grinder Cicada)
**Epic Type:** Implementation Epic

## Scope
This epic will add an SMS channel to the Notification Service to enable SMS delivery.
It will include:
- Schema definition for an SMS notification event
- Adding the schema to `ghga-event-schemas`
- Functionality for consuming those events and dispatching notifications via an SMS gateway

It does not include:
- Changing existing services to send SMS notification events
- Updating the Notification Orchestration Service to emit SMS notification events

## Additional Implementation Details

### SMS Notification Event
An SMS notification event schema will be defined in the `ghga-event-schemas` repository.  
The event schema will detail all the information needed to send a notification via SMS:
- `text` (required)
- `phone` (required)

The exact field names and constraints will be provided in the `ghga-event-schemas` repository, which is considered the source of truth.
This information will be used to create an SMS with a consistent format.

### Notification Service
This is a microservice dedicated to consuming notification events from the "notifications" topic in Kafka.
In this update, a new type of notification event will be added to expand the service's capabilities. 

To utilize the Notification Service to send SMS, publishers will need to publish an event to the "notifications" topic using the "SMS notification" event type, with a payload conforming to the schema defined by `SmsNotification` in the `ghga-event-schemas` repository.

SMS will be sent via HTTP, and SMS contents will be injected into the requests. The parameters required to successfully configure the service are as follows:
- `lox24_host`: The address of the SMS gateway
- `lox24_port`: The port to use
- `lox24_token`: The API token used for authentication and authorization
- `lox24_sender_id`: The sender's ID or phone number
- `lox24_auth_token_header`: The header used for the API token
- `lox24_timeout`: The timeout used for the requests
- `lox24_sms_send_path`: The API path to send SMS
  
## Human Resource/Time Estimation

- Number of sprints required: 1
- Number of developers required: 1
