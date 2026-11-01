[![CI](https://github.com/bluesky/bluesky-interfaces/actions/workflows/ci.yml/badge.svg)](https://github.com/bluesky/bluesky-interfaces/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/bluesky/bluesky-interfaces/branch/main/graph/badge.svg)](https://codecov.io/gh/bluesky/bluesky-interfaces)
[![PyPI](https://img.shields.io/pypi/v/bluesky-interfaces.svg)](https://pypi.org/project/bluesky-interfaces)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)

# bluesky_interfaces

Data model used by the bluesky ecosystem.

A primary design goal of bluesky is to enable better research by recording
rich metadata alongside measured data for use in later analysis. Documents are
how we do this.

This repository contains the formal schemas for bluesky's streaming data model
and some Python tooling for composing, validating, and transforming documents
in the model.

What            | Where
:---:           | :---:
Source          | <https://github.com/bluesky/bluesky-interfaces>
PyPI            | `pip install bluesky-interfaces`
Documentation   | <https://bluesky.github.io/bluesky-interfaces>
Releases        | <https://github.com/bluesky/bluesky-interfaces/releases>

## Where is my data?

For the full details and schema please see the `data_model` section.  This is a very quick guide to where
you should look for / put different kinds of information

* Information about your sample that you know before the measurement → *Start* Document
* What experiment you intended to do → *Start* Document
* Who you are / where you are → *Start* Document
* References to external databases → *Start* Document
* The Data™  → *Event* Document
* Detector calibrations, dark frames, flat fields , or masks  → *Event* Document (probably in its own stream)
* The shape / data type / units of The Data™  → *Event Descriptor* Document in the *data_keys* entry
* Anything you read from the controls system that is not device configuration  → *Event* Document
* Device configuration data  → *Event Descriptor* Document in the *configuration* entry

<!-- README only content. Anything below this line won't be included in index.md -->

See <https://bluesky.github.io/event-model> for more detailed documentation.
