# Quote delivery

The website contact page and standalone https://quote.thealytouch.co.uk/ questionnaire use the existing FormSubmit receiver for contact@thealytouch.co.uk. No new receiver is introduced.

Text-only requests use AJAX and require an affirmative JSON success response. This confirms receiver acceptance, not inbox delivery. Both forms validate all steps, render customer text safely, prevent concurrent submissions, check/pass a honeypot, and preserve answers on AJAX failures. Requests time out after 20 seconds. Honeypots do not replace server-side abuse controls.

The main form supports six images within a combined 10MB limit. Photo requests use native multipart form submission with attachment fields and return to /thank-you.html. The browser navigates through FormSubmit. Do not fetch that HTML endpoint cross-origin or infer delivery from words in its response.

Reference: https://formsubmit.co/documentation

Before treating delivery as verified, obtain authorization for labelled test enquiries and ask Aly to confirm receipt, reply details and attachments. Mocked tests do not verify activation, spam filtering or inbox delivery. Publish the main privacy and thank-you pages before the standalone update.
