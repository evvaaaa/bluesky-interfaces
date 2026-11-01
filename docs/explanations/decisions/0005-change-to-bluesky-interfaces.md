# 4. Change to bluesky-interfaces

## Status

Accepted

## Context

We should include protocols alongside documents in a new repo/package bluesky-interaces.

## Decision

We have decided to convert to a new repo containing protocols and documents to facilitate interface standardization and typing across the ecosystem.

## Consequences

* event-model will be moved into a new repo alongside history, maintaining optional imports for it's various components.
* event-model will be achived.
* `bluesky.protocols` will be moved into this repo, maintaining git history.
* `bluesky.protocols` will forward from `bluesky_interaces.protocols` with a deprecation warning.
