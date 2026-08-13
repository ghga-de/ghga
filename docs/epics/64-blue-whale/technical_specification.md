# Reimplement frontend features in Angular (Blue Whale)

**Epic Type:** Implementation Epic

Epic planning and implementation follow the
[Epic Planning and Marathon SOP](https://ghga.pages.hzdr.de/internal.ghga.de/main/sops/development/epic_planning/).

## Scope

### Outline:

The goal of this epic is to implement all the features from the current React-based GHGA Data Portal in Angular, using the baseline application that has been built in the [Hippopotamus](../60-hippopotamus/technical_specification.md) as the starting point.

### Included/Required:

- Full implementation of all features of the React-based GHGA Data Portal
- Unit tests and end-to-end tests (against the mock backend) for these features

### Optional:

- Some features or change requests proposed for the existing GHGA Data Portal
- Full test coverage

### Not included:

- Automated end-to-end tests against the real backend

## Details:

This section outlines a checklist of all features to be implemented, divided into several steps. A pre-release should be published upon the completion of each step. Final releases should begin with version 2 to distinguish them from the legacy frontend, which uses version numbers in the version 1 range.

### Already implemented

The following parts are already contained in the baseline application that has been created in the [Hippopotamus](../60-hippopotamus/technical_specification.md) epic.

- Homepage
	- Global Stats
- Header and Footer
- Dataset browser (partial)
- Auth Service
- Error message handling
- User Login:
	- Login/Logout buttons
	- OIDC callback URL
	- User registration
	- 2FA setup
	- 2FA confirmation
- Metadata service
- Metadata search service (partial)

We have also added rudimentary unit tests and end-to-end tests. While implementing the remaining functionality in the following four steps, basic tests should be included together with the implemented functionality. As a last step, the implementation and tests should be refined.

### Step 1: Catalog functionality

In this epic, we first implement functions from the GHGA Catalog.

- [ ] Metadata search service (complete)
- [ ] Dataset browser (complete)
	- [ ] Result list (loading indicator, tests)
	- [ ] Dataset summaries
	- [ ] Filter (facets)
	- [ ] Search
 - [ ] Single dataset view
	 - [ ] Summary
	 - [ ] Study
	 - [ ] Publications
	 - [ ] Dataset access policy
- [ ] Access Request Service
- [ ] Access request
	 - [ ] Button to request access
	 - [ ] Access request form

## Step 2: Access Requests

We implement the functionality of the account page in the next step:

- [ ] IVA service
- [ ] Account (user profile) page
	- [ ] Email address
	- [ ] Contact addresses (IVAs)
		- [ ] Create
		- [ ] Request verification
		- [ ] Confirm verification code
		- [ ] Delete
	- [ ] Accessible datasets
	- [ ] Pending access requests

## Step 3: Download

We complete the user facing functionality by implementing the function to create a work package:

- [ ] Work packages
    - [ ] Work package service
	- [ ] Creation form
	- [ ] Token generation

## Step 4: Data steward tools

Finally, we add the tooling for the data stewards:

- [ ] Access request manager
	- [ ] List
	- [ ] Filter
	- [ ] Detail
- [ ] IVA manager
	- [ ] List
	- [ ] Filter
	- [ ] (Re)create code
	- [ ] Invalidation
	- [ ] Confirm transmission

### Polish and improve test coverage

In the last step, we polish everything (edge cases, layout etc.), make sure that the app is usable on small screens (which may take some days), and increase the test coverage from unit tests and end-to-end tests. The latter should cover the complete user journey from dataset discovery to dataset download, but they should use the static (stateless) mock backend that is part of the frontend repository.

### Full end-to-end testing

The following is not considered part of this epic any more, but crucial.

Before replacing the legacy application, the new frontend must be thoroughly tested against the real backend (manually, using the staging environment). Data stewards and other team members could help with testing at this point.

If everything looks good, the frontend can be replaced in production.

Afterwards, automated end-to-end tests against the real backend (using the testing environment) should be created and integrated into the existing Archive Test Bed (which so far does not cover the frontend). We could reuse parts of the end-to-end tests from the frontend repository, translating them from JavaScript to Python and adapting them to the data used in the Archive Test Bed. This will allow us to reduce the repeated manual testing before releasing new frontend versions in the future.

## Human Resource/Time Estimation:

Number of sprints required: 3

Number of developers required: 3
