# TODO
Kohaku-Hub is a pretty large project and really hard to say where to start is better, but I will try to list all the known TODOs here with brief priority note


- [ ] Basic Infra Structure
    - [x] LakeFS + MinIO deployment
    - [x] MinIO presigned URL
    - [ ] ...TBA...
- [ ] API layer
    - [x] Upload
        - [x] Upload small file (not LFS)
        - [x] Upload large file
    - [x] Download
        - [x] Direct http requests (with S3 presigned url)
        - [ ] Other special interface (if have)
    - [x] Deletion
    - [ ] Repository Managements
        - [x] Tree List
        - [x] Creation
        - [x] Deletion
        - [ ] Move/Modify name
        - [ ] ...TBA...
    - [x] User Auth System
    - [ ] Organization/Visibility
    - [ ] ...TBA...
- [ ] Basic webUI
    - [ ] User dashboard
    - [ ] ...TBA...