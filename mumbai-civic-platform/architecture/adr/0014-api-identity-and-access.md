# ADR 0014: API behind CloudFront and a load balancer; Cognito for sign-in; tiers enforced in the query layer

**Status:** Accepted · 15 November 2026

## Options

| Concern | Option | For | Against |
|---|---|---|---|
| Entry | **CloudFront, WAF, Application Load Balancer to Fargate** | Streaming responses; one path for site and api; caching | Fixed cost of a load balancer |
| | API Gateway to Fargate or Lambda | Usage plans and keys built in | Response-time and streaming limits; extra hop |
| Identity | **Amazon Cognito** | Managed; phone and email sign-in; groups map to tiers | Limited customisation |
| | Keycloak on Fargate | Open, flexible | Another service and database to run and secure |
| Authorisation | In the application only | Simple | Easy to miss a path |
| | **Tier labels on data, filtered in the query layer** | An agent or endpoint cannot return what its tier may not see | Every query path must go through the layer |

## Decision

CloudFront with WAF in front of an Application Load Balancer. Cognito user pools with groups for contributor, researcher, official and reviewer; anonymous use is the public tier. Every read goes through the query layer, which adds the caller's tier to the query. Public API keys and rate limits are handled in the api service.

## Consequences

- No service other than the loader and the query layer holds database credentials.
- Researcher and official accounts are approved by a person.
