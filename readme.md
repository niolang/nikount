# Abstract
**Nikount** is a small Flask web application to manage shared expenses during a trip, weekend, holiday, or group event.
The app is designed to be simple: no user accounts, no frontend framework, and access through secure role-based links.
## Features
### Sessions
A session represents one shared event, for example a weekend with friends.
Features:
- create a new session
- generate access links for different roles
- manage session statuses:
  - `open` : add/remove/edit expenses
  - `frozen` : only reimbursments are available
  - `closed` : automatic status meaning all reimbursments were done
### Roles
Nikount supports two main session roles:
- `admin`
- `viewer`
There is also a password-protected superadmin area to overview and manage all sessions.
### Admin features
Admins can:
- add participants
- delete participants (they have to be unused)
- add expenses
- edit expenses
- delete expenses
- approve or reject expenses submitted by viewers
- freeze a session
- reopen a frozen session
- view computed reimbursements
- mark reimbursements as done
### Viewer features
Viewers can:
- view participants and expenses
- submit expenses
- edit their own submitted expenses while allowed
### Reimbursements
Nikount computes balances and reimbursement operations based on approved expenses.
It supports:
- splitting expenses between selected participants
- computing who owes money to whom
- marking reimbursements as done
- automatically closing a frozen session when no reimbursement remains
### Superadmin
The superadmin page allows global administration of sessions.
Access URL:
/superadmin-access
