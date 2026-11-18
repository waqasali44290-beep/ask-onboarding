# Deployments

Merges to main deploy automatically to staging. Production deploys happen through the deploy pipeline in GitHub Actions, Monday to Thursday between 09:00 and 16:00. No production deploys on Fridays or before public holidays, except hotfixes approved by the on-call engineer.

If a deploy causes errors, roll back first using the "Rollback" button in the pipeline, then investigate.
