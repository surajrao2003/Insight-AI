# AKS CI/CD Deployment Reference Guide - InsightAI Platform

This document explains every field used in the following files:

```text
k8s/deployment.yaml
k8s/service.yaml
.github/workflows/deploy.yml
```

The goal is to understand not only what each field does, but also why we are using it in our Investor Intelligence Platform project.

---

# deployment.yaml

## Complete File

```yaml
apiVersion: apps/v1
kind: Deployment

metadata:
  name: insightai

spec:
  replicas: 1

  selector:
    matchLabels:
      app: insightai

  template:
    metadata:
      labels:
        app: insightai

    spec:
      containers:
      - name: insightai

        image: insightai.azurecr.io/insightai:latest

        imagePullPolicy: Always

        envFrom:
        - secretRef:
            name: insightai-secrets

        ports:
        - containerPort: 8000
```

---

## apiVersion

```yaml
apiVersion: apps/v1
```

This tells Kubernetes which API group should process this resource. Deployments belong to the `apps/v1` API group. Whenever Kubernetes reads this file, it knows that this resource should be handled by the Deployment controller.

---

## kind

```yaml
kind: Deployment
```

This tells Kubernetes what resource to create.

In Kubernetes, everything is represented as a resource.

Examples:

```text
Deployment
Service
Secret
ConfigMap
Ingress
```

In our case we want Kubernetes to create and manage application pods, therefore we use a Deployment resource.

---

## metadata

```yaml
metadata:
  name: insightai
```

This is the unique name of the deployment inside the cluster.

We use this name later when checking deployment status, restarting deployments, viewing logs, and troubleshooting.

Examples:

```bash
kubectl get deployment insightai
kubectl rollout restart deployment/insightai
kubectl describe deployment insightai
```

Think of this as the identifier for our application deployment.

---

## replicas

```yaml
replicas: 1
```

This defines how many copies of the application should be running.

For our project we use:

```yaml
replicas: 1
```

to reduce Azure costs while demonstrating the deployment process.

In production systems this is usually increased.

Example:

```yaml
replicas: 3
```

This would create three identical application pods.

If one pod crashes, the remaining pods continue serving users.

---

## selector

```yaml
selector:
  matchLabels:
    app: insightai
```

The deployment needs a way to identify which pods belong to it.

The selector tells Kubernetes:

```text
Manage all pods having app=insightai
```

This creates the relationship between the deployment and its pods.

The selector must match the labels defined inside the pod template.

---

## template

```yaml
template:
```

The template section acts as the blueprint used to create pods.

Whenever Kubernetes needs to create a new pod, it uses the configuration defined inside this section.

Think of this as a manufacturing template.

Every pod created by the deployment will follow this template.

---

## labels

```yaml
labels:
  app: insightai
```

Labels are tags attached to Kubernetes resources.

Here we are assigning:

```text
app=insightai
```

to all application pods.

These labels are later used by:

```text
Deployments
Services
Monitoring Tools
Ingress Controllers
```

to identify resources.

---

## container name

```yaml
name: insightai
```

This defines the container name inside the pod.

This name is mainly used for:

```text
Logging
Debugging
Monitoring
Container Identification
```

When multiple containers exist inside a pod, this name becomes important.

---

## image

```yaml
image: insightai.azurecr.io/insightai:latest
```

This tells Kubernetes where the application image is stored.

Breakdown:

```text
Registry    : insightai.azurecr.io
Repository  : insightai
Tag         : latest
```

When a pod starts, AKS downloads this image from Azure Container Registry.

This image contains:

```text
Application Code
Python Runtime
Dependencies
Libraries
```

Everything required to run the application.

---

## containerPort

```yaml
containerPort: 8000
```

This tells Kubernetes that the FastAPI application is listening on port 8000 inside the container.

This port is internal to the container.

Users will never directly access this port.

Instead:

```text
Load Balancer
↓
Service
↓
Container Port 8000
```

---

## imagePullPolicy

```yaml
imagePullPolicy: Always
```

This instructs Kubernetes to always check ACR for the latest image before starting a pod.

This is useful during CI/CD because every deployment automatically pulls the newest image.

Without this, Kubernetes may reuse an older cached image.

---

## envFrom

```yaml
envFrom:
- secretRef:
    name: insightai-secrets
```

This injects every key inside the `insightai-secrets` Kubernetes Secret into the container as environment variables.

Our application needs values such as:

```text
AZURE_OPENAI_ENDPOINT
AZURE_OPENAI_API_KEY
AZURE_SEARCH_ENDPOINT
POSTGRES_HOST
POSTGRES_PASSWORD
```

Rather than hardcoding these into the deployment file, we reference the Secret created by the CI/CD pipeline.

This keeps sensitive configuration out of version control while still making it available to the running application.

---

# service.yaml

## Complete File

```yaml
apiVersion: v1
kind: Service

metadata:
  name: insightai

spec:
  selector:
    app: insightai

  type: LoadBalancer

  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
```

---

## apiVersion

```yaml
apiVersion: v1
```

Services belong to the Kubernetes Core API group, which uses `v1`.

This tells Kubernetes which API should handle the Service resource.

---

## kind

```yaml
kind: Service
```

Creates a networking layer for our application.

Without a Service:

```text
Pods Exist
Application Exists
Users Cannot Access It
```

The Service acts as the bridge between users and application pods.

---

## metadata

```yaml
metadata:
  name: insightai
```

This becomes the name of the Service.

Useful commands:

```bash
kubectl get svc
kubectl describe svc insightai
```

---

## selector

```yaml
selector:
  app: insightai
```

The Service must know which pods should receive traffic.

This selector tells Kubernetes:

```text
Forward traffic to pods having app=insightai
```

Since our deployment creates pods with:

```yaml
labels:
  app: insightai
```

the Service can automatically discover them.

---

## type

```yaml
type: LoadBalancer
```

This is one of the most important settings.

Azure automatically creates:

```text
Public IP
Azure Load Balancer
```

when this type is used.

Without LoadBalancer:

```text
Application Remains Internal
```

With LoadBalancer:

```text
Internet Users Can Access Application
```

---

## protocol

```yaml
protocol: TCP
```

Specifies the network protocol used for communication.

Web applications typically use:

```text
TCP
```

because HTTP and HTTPS are built on top of TCP.

---

## port

```yaml
port: 80
```

This is the public port exposed to users.

Users access:

```text
http://<public-ip>
```

which automatically uses port 80.

---

## targetPort

```yaml
targetPort: 8000
```

The Service forwards incoming traffic to the FastAPI application running on container port 8000.

Traffic flow:

```text
User
 ↓
Public IP
 ↓
Port 80
 ↓
Service
 ↓
Port 8000
 ↓
FastAPI Application
```

---

# deploy.yml

## Complete File

```yaml
name: Build and Deploy to AKS

on:
  push:
    branches:
      - cicd-setup

jobs:

  build-and-deploy:

    runs-on: ubuntu-latest

    steps:

      - name: Checkout Repository
        uses: actions/checkout@v4

      - name: Azure Login
        uses: azure/login@v2
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}

      - name: Login to ACR
        run: |
          az acr login --name ${{ secrets.ACR_NAME }}

      - name: Build Docker Image
        run: |
          docker build \
            -t ${{ secrets.ACR_LOGIN_SERVER }}/insightai:latest .

      - name: Push Docker Image
        run: |
          docker push \
            ${{ secrets.ACR_LOGIN_SERVER }}/insightai:latest

      - name: Get AKS Credentials
        run: |
          az aks get-credentials \
            --resource-group ${{ secrets.AKS_RESOURCE_GROUP }} \
            --name ${{ secrets.AKS_CLUSTER_NAME }} \
            --overwrite-existing

      - name: Deploy Application
        run: |
          kubectl apply -f k8s/deployment.yaml
          kubectl apply -f k8s/service.yaml

      - name: Restart Deployment
        run: |
          kubectl rollout restart deployment/insightai

      - name: Verify Rollout
        run: |
          kubectl rollout status deployment/insightai
```

---

## Workflow Name

```yaml
name: Build and Deploy to AKS
```

The name displayed inside GitHub Actions.

This helps identify the workflow in the Actions dashboard.

---

## Trigger

```yaml
on:
  push:
    branches:
      - cicd-setup
```

This tells GitHub when to execute the pipeline.

Whenever code is pushed to:

```text
cicd-setup
```

the workflow automatically starts.

---

## runs-on

```yaml
runs-on: ubuntu-latest
```

GitHub creates a temporary Ubuntu virtual machine to execute all pipeline steps.

Think of this as a temporary build server.

---

## Checkout Repository

```yaml
uses: actions/checkout@v4
```

Downloads the source code into the GitHub runner.

Without this step:

```text
Dockerfile Not Available
Source Code Not Available
Build Fails
```

---

## Azure Login

```yaml
uses: azure/login@v2
```

Authenticates GitHub Actions with Azure.

This step allows the pipeline to:

```text
Access AKS
Access ACR
Execute Azure CLI Commands
```

To authenticate, this action needs a service principal, which is created inside Microsoft Entra ID.

Create the service principal using Azure CLI or via Azure portal:

```bash
az ad sp create-for-rbac --name "insightai-github-actions" --role contributor --scopes /subscriptions/<subscription-id>/resourceGroups/insight-ai-resource-group --sdk-auth
```

This outputs a JSON object containing the credentials needed by `azure/login@v2`.

Note that the `--role contributor` flag above grants the `insightai-github-actions` application the Contributor role assignment on the `insight-ai-resource-group` scope. Without this role assignment, the pipeline can authenticate but will be denied permission when it tries to push images, deploy resources, or manage the AKS cluster.

Add this JSON as a GitHub secret:

```text
GitHub Repository
  → Settings
    → Secrets and variables
      → Actions
        → New repository secret
```

Name the secret:

```text
AZURE_CREDENTIALS
```

Paste the value in the following format:

```json
{
  "clientId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "clientSecret": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "subscriptionId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "tenantId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
}
```

The workflow reads this secret through:

```yaml
creds: ${{ secrets.AZURE_CREDENTIALS }}
```

Without this secret, `azure/login@v2` cannot authenticate and every subsequent Azure CLI or `kubectl` step in the pipeline fails.

---

## Login to ACR

```yaml
az acr login
```

Authenticates Docker against Azure Container Registry.

Without this step:

```text
Docker Push Fails
Unauthorized Error
```

---

## Build Docker Image

```yaml
docker build
```

Creates a Docker image from:

```text
Dockerfile
Source Code
Requirements
Dependencies
```

This produces a deployable container image.

---

## Push Docker Image

```yaml
docker push
```

Uploads the Docker image to Azure Container Registry.

After this step:

```text
AKS Can Pull The Image
```

---

## Get AKS Credentials

```yaml
az aks get-credentials
```

Connects GitHub Actions to the AKS cluster.

This command automatically configures kubectl to communicate with the cluster.

Without this step:

```text
kubectl Cannot Access AKS
```

---

## Create Kubernetes Secrets

```yaml
kubectl create secret generic insightai-secrets \
  --from-literal=... \
  --dry-run=client -o yaml | kubectl apply -f -
```

Builds the `insightai-secrets` Secret from GitHub repository secrets and applies it to the cluster, so the pod's `envFrom` can inject them at runtime.

If you add, rename, or remove any `--from-literal` value here, update the matching GitHub repository secret too.

---

## Deploy Application

```yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
```

Creates the resources if they don't exist.

Updates them if they already exist.

This is why we do not need:

```bash
kubectl create deployment
kubectl expose deployment
```

manually.

Sometimes the deployment may fail because pods are unable to pull the image from ACR, shown as `ImagePullBackOff` or `ErrImagePull` when running:

```bash
kubectl get pods
```

If this happens, follow Step 9 in `deployment-Document.md` (Create Image Pull Secret) to create/patch the `acr-secret` and attach it to the default service account.

---

## Restart Deployment

```yaml
kubectl rollout restart deployment/insightai
```

Forces Kubernetes to recreate pods using the latest image from ACR.

This ensures newly pushed images are picked up immediately.

---

## Verify Rollout

```yaml
kubectl rollout status deployment/insightai
```

Waits until deployment completes successfully.

This acts as a health check for the deployment process.

If the deployment fails, the GitHub Action also fails.
