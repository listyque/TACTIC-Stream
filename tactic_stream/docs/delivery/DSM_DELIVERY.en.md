# TACTIC Stream on Synology DSM

The `.spk` installs Stream, Apache and PostgreSQL through Synology Container Manager.
It contains the Linux images, so it does not download application dependencies during
installation. Use an **x86-64 NAS, DSM 7.2.1 or newer, and Container Manager**.
ARM NAS models are not supported by this package.

This is a **preview for a new installation**. Its Compose deployment and lifecycle
scripts have automated checks; installation through Package Center on a physical
Synology device still needs acceptance. It refuses an upgrade or reuse of retained
data. Keep an existing server running separately until an explicit migration has
been tested with its backup.

## Install

1. Download the clean or demo SPK from [Releases](https://github.com/listyque/TACTIC-Stream/releases).
2. Open Package Center → Manual Install and select the SPK.
3. Choose an unused HTTP port and a new administrator password. The login is `admin`.
4. Start the package. Container Manager initializes the database; the demo edition
   also creates its projects and publishes their images. Allow this first start to finish.
5. Open the package's shortcut or `http://NAS-address:port/`.

The defaults are **8882** for clean and **8884** for demo. They have separate package
identities and Docker projects, so both can be installed together. Clean starts
without business projects. Demo contains Orbit Studio and Atlas Reference Library,
versioned pictures, tasks, people, workflow, Knowledge Base and two example plugins.
Sign in as admin first. Generated demo user passwords are in
`/var/packages/TacticStreamDemo/var/data/stream/demo-accounts.json`.

Handler connects to this HTTP address using its own server preset and login.
The DSM package does not install a desktop client on the NAS.

## Data and access

Only the application's HTTP port is published. PostgreSQL, backend workers and
Webmin have no published NAS ports. For HTTPS use DSM Reverse Proxy; keep the HTTP
port restricted to a trusted network. This package does not change NAS firewall,
router, certificates, existing shares or other Docker projects.

Project files, server configuration and PostgreSQL data are under
`/var/packages/TacticStream/var/data` (or `TacticStreamDemo`). Deployment secrets
are under the adjacent private `secrets` directory. Apache/Webmin configuration
uses the package project's Docker volumes. Package scripts run as the package user;
Container Manager owns the containers. Initialization uses container root only to
prepare its mounted data directory, then switches to the Stream application user.

Stop the package before a cold backup. Back up the complete persistent `var` directory
and the project's Apache/Webmin volumes together. Stopping or removing the package
does not run a data cleanup script. Reinstallation refuses retained data rather than
resetting it; restoring a server requires its matching database, repository and secrets.
Do not treat reinstalling an older SPK as a database rollback.

## Build

Build a [Docker delivery](https://github.com/listyque/TACTIC-Stream/wiki/Server), then run from `tactic_stream`:

```sh
python -m tools.dsm_delivery --server /path/to/server-package --output /path/to/TACTIC-Stream-DSM.spk
```

The builder verifies the source package's inventory, carries its clean/demo edition
into the SPK, and writes an adjacent SHA-256 checksum. It uses Synology's
[Docker Project Worker](https://help.synology.com/developer-guide/resource_acquisition/docker-project.html)
and [package environment](https://help.synology.com/developer-guide/synology_package/script_env_var.html).
