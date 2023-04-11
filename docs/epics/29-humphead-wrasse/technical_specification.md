# Notification Service (Humphead Wrasse)
**Epic Type:** Implementation Epic

## Scope:
This epic will include a microservice that will listen for events instructing it to send notifications to users.
It will include:
- Schema definition for email notification events
- Adding the schema to ghga-event-schemas
- Functionality for consuming those events and dispatching notifications via email

It does not include:
- Changing existing services to send notification events
- Alternative notification event types (i.e. only email notifications are supported in this epic)

## Additional Implementation Details:

### Email Notification Event
An EmailNotification event schema will be defined in the ghga-event-schemas repository.
The event schema will detail all the information needed to send a notification via email:
- email address of primary recipients (required)
- secondary (cc'd) recipient email addresses (optional)
- tertiary (bcc'd) recipients email addresses (optional)
- subject line (required)
- name of the recipient (required)
- plaintext email body (required)
The exact field names and constraints will be provided in the ghga-event-schemas repository, which is considered the source of truth.
This information will be used to create an email with a consistent format.

### Notification Service
This is a microservice dedicated to consuming EmailNotification events from the "notifications" topic in kafka.
Other types of notification events will not be handled by this service at this time, but the service could be expanded in the future if needed.
In order to utilize the notification service to send emails, publishers will need to publish an event to the "notifications" topic using the "email_notification" event type, with a payload conforming to the schema defined by EmailNotification in the ghga-event-schemas repository.
Emails will be sent via SMTP, and email contents will be injected into a configurable jinja2 template. The parameters required to successfully configure the service are as follows:
- smtp_host: The Host portion of the connection string for the server
- smtp_port: The port to use
- login_email: Email used to log in to the email server
- login_password: The password used to log in
- sender_address: Sender's email address (if different from login address)
- template_name: Name of the jinja2 HTML template file (e.g. "email_template.html")
  - The template should be stored in ns/templates/
  - The template should use the following template variables:
    - recipient: The name of the recipient (e.g. "Dear {{ recipient }},...")
    - body: The body text of the email, located between the greeting and signature
    - If the template variables are not named correctly, the HTML version of the email will not be generated correctly.

## Human Resource/Time Estimation:

Number of sprints required: 1

Number of developers required: 1
