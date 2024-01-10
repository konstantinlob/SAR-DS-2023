> ## Please note
> This file was used during development to plan the implementation.
> It contains the notes of the development team and is not meant as a form of documentation.
> 
> This file is only included for completeness.

- [x] ~~(properly handle Clients with missing permissions) _this is not really necessary assuming the client does not
      send malicious requests after being denied authentication_~~
- [ ] (don't hardcode the Client port) _this is not a problem since the requirements only ask for one client anyways_
- [x] ~~how to handle messages from restarted senders? right now the r_broadcast middleware discards them because the
      message ID is already known for this sender~~
- [x] ~~accept messages of any length, don't try to read into fixed-length buffer~~
- [ ] (handle errors that occur in backup servers when the client makes changes to files that are not present on the
      backup server) _it was decided that this is out of scope for this project_