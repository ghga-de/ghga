# Notification Service (Humphead Wrasse)
**Epic Type:** Implementation Epic

## Scope:
This epic will include a microservice that will listen for events instructing it to send notifications to users.
It will include:
- Schema definition for notification events
- Adding the schema to ghga-event-schemas
- Functionality for consuming those events and dispatching notifications via email

It does not include:
- Changing existing services to send notification events
- Alternative notification event handling (i.e. only email notifications are supported in this epic)

## Additional Implementation Details:

### Notification Event
A Notification event schema will be defined in the ghga-event-schemas repository.
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
This is a microservice dedicated to consuming Notification events from the "notifications" topic in kafka.
Other types of notification events will not be handled by this service at this time, but the service could be expanded in the future if needed.
In order to utilize the notification service to send emails, publishers will need to publish an event to the "notifications" topic using the "notification" event type, with a payload conforming to the schema defined by Notification in the ghga-event-schemas repository.
Emails will be sent via SMTP, and email contents will be injected into configurable templates. The parameters required to successfully configure the service are as follows:
- smtp_host: The Host portion of the connection string for the server
- smtp_port: The port to use
- login_user: Username or email address used to log in to the SMTP server
- login_password: The password used to log in
- sender_address: Sender's email address (if different from login address)
- plaintext_email_template: The email template to use for the plaintext email version.
- html_email_template: The email template to use for the HTML email version.
  - BOTH the html and plaintext template should use template variables with the same name as the event keys:
    - Variables are formed in the template like $variable_name. Consider the following:
      - $recipient_name: The name of the recipient (e.g. "Dear $recipient_name,...")
      - $plaintext_body: The body text of the email, located between the greeting and signature. Nothing here will be further substituted, so don't include any variables within this section.
    - If the template variables are not named correctly, the email will not be generated correctly.

## Human Resource/Time Estimation:

Number of sprints required: 1

Number of developers required: 1
