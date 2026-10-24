# File workspace qualification

[File project delivery](FILE_PROJECT_DELIVERY.en.md) defines installation and
public limitations. [Workspace scope](FILE_WORKSPACE_SCOPE.md) distinguishes
Handler's native operations from Stream server/browser responsibilities.
[Recovery acceptance](RECOVERY_ACCEPTANCE.md) records the versions and environments
actually qualified for upgrade, backup and restore.

A new qualification must identify both product versions, package hashes,
configuration, database vendor, exact commands and fixture scope. Record outcomes
and unresolved failures separately. Exercise real native input and file effects
for Handler, applicable browser/server operations for Stream, and permission,
revision/conflict, cancellation and rollback behavior. Use isolated data; clean
up all fixture processes. Never relabel old counts or a same-version reinstall
as fresh acceptance or an upgrade from a prior release.
