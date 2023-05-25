The work package service allows creating work packages for downloading or
uploading dataset files and provides an authorization mechanism for these tasks
by issuing access and work order tokens.

### API endpoints:

#### `POST /work-packages`

Creates a work package.

- auth header: internal access token
- request body:
  - `dataset_id`: string (the ID of a dataset)
  - `type`: enum (download/upload)
  - `file_ids`: array of strings  (null = all files of the dataset)
  - `user_public_crypt4gh_key`: string (the user's public Crypt4GH key)
- response body:
  - `id`: string (the ID of the created work package)
  - `token`: string (encrypted work and base64 encoded package access token)

####  `GET /work-packages/{work_package_id}`

Gets details on the specified work package.

- auth header: work package access token

#### `POST /work-packages/{work_package_id}/files/{file_id}/work-order-tokens`

 Creates an encrypted work order token for the specified work package and file.

- auth header: work package access token

#### `GET /users/{user_id}/datasets`

Gets a list of all dataset IDs that can be downloaded by the user.

- auth header: internal access token with the user context
