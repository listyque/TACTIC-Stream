# Demonstration projects

[Русский](README.ru.md)

The demo edition creates two fictional projects in a new Stream installation.
Open the same server in the browser and Handler to see the same records and files.

- **Orbit Studio**: six assets, a sequence and three shots; model, lookdev and review
  stages; assigned tasks with dates; notes and published images. Survey Drone has
  a second lookdev publication, so its version history is populated.
- **Atlas Reference Library**: three reference assets with their own tasks, notes
  and publications. Switching projects changes the working context.
- **People**: Maya Chen and Leo Martins can edit records. Nora Kim can read them.
  Passwords are generated for each installation and stored in the server data
  directory's `demo-accounts.json`. The administrator password is chosen at setup.
- **Plugins**: [Studio Review](../studio_review/README.md) adds a review board and
  sample review records. Workspace Pulse adds a project dashboard. Both are real
  installed packages, with their scripts and UI resources available for inspection.
- **Knowledge Base**: each project has a published starting article linked to an asset.

Start with **Item View**, open Survey Drone, inspect its tasks and publications, then
open the task workspace/Gantt and the plugins' pages. Sign in as Nora to compare
permissions. These are examples you can edit; they are not a copy of a studio database.
The six PNG illustrations in `assets` were created for this project's presentation
and are included as fictional sample content under the repository's license.

Demo content is a separate, checksummed payload. The initializer refuses an existing
business project; successful repeated initialization preserves changes and passwords.
If first initialization fails halfway, keep its logs and data for diagnosis and retry
in a new empty data directory. It does not delete a partially created project for you.

To prepare the payload from a checkout:

```sh
cd tactic_stream
python -m tools.demo_delivery --output /path/to/new/demo
python -m tactic_stream --data-dir /path/to/new/data init --demo /path/to/new/demo
```

The [Windows](../../tactic_stream/docs/delivery/WINDOWS_DELIVERY.en.md),
[Docker](../../tactic_stream/docs/delivery/SERVER_DELIVERY.en.md) and
[DSM](../../tactic_stream/docs/delivery/DSM_DELIVERY.en.md) demo packages run this
initialization during setup. Clean packages omit the demo payload.
