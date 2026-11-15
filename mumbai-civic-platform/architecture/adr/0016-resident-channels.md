# ADR 0016: WhatsApp through AWS End User Messaging Social; Transcribe for voice notes

**Status:** Accepted for WhatsApp text; speech pending tests · 15 November 2026

## Context

Many residents will use WhatsApp, often by voice note in Marathi or Hindi.

## Options

| Concern | Option | For | Against |
|---|---|---|---|
| WhatsApp | **AWS End User Messaging Social** | In the same account and IAM; an endpoint exists in Mumbai; events arrive on SNS | Newer service; WhatsApp Business onboarding with Meta still applies |
| | Meta Cloud API direct | No intermediary | Webhook hosting and token handling are ours |
| | Twilio or another provider | Mature tooling | Extra vendor and cost |
| Speech to text | **Amazon Transcribe, batch** | AWS lists Marathi and Hindi for batch jobs, and a voice note is a batch job | Accuracy on local place names is unknown |
| | Open Indic models (AI4Bharat) on our compute, or the government's Bhashini service | Built for Indian languages | Operations, or dependence on an external service |
| Text to speech | Amazon Polly | Hindi voices exist | I found no Marathi voice |
| | Open Indic text-to-speech | Marathi available | Operations |

## Decision

WhatsApp through AWS End User Messaging Social. Voice notes are transcribed with Amazon Transcribe in batch mode; the transcript's place names are matched against the glossary and read back for confirmation before answering. Replies are text first. Spoken replies in Marathi are deferred until an open Indic model has been tested.

## Consequences

- Messages are redacted before storage ([ADR 0018](0018-security-and-privacy.md)).
- WhatsApp's rules on message templates and reply windows shape how alerts are sent.

## To confirm

Transcribe accuracy on fifty real Marathi voice notes; WhatsApp Business account approval for the host organisation.
