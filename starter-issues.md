# Starter Issues for Confluence AI Assistant

This file collects suggested **bugs, enhancements, and documentation tasks** that contributors can pick up.  
If you’re new here, check out these issues before creating a pull request. Many are tagged as **good first issue**.

---

## 🐛 Bugs / Fixes

### 1. Improve error handling for missing/invalid Confluence API keys
**Labels:** bug, good first issue  

Right now, if a Confluence API key is missing or invalid, the app just fails silently or throws a raw error.  

👉 Expected behavior: provide a clear error message like:  Error: Missing or invalid Confluence API key. Please set it via environment variables or .env file.

---

### 2. Handle Docker-in-Docker limitation gracefully
**Labels:** bug, enhancement  

Running `demo_app.py` on hosted platforms (e.g., Railway, Render) fails because Docker-in-Docker isn’t supported.  

👉 Enhancement idea: detect hosted environments and either:  
- Fall back to a local subprocess, OR  
- Provide a message with deployment alternatives (Kubernetes, local Docker, etc.).  

---

## 🚀 Enhancements

### 3. Add a simple web UI frontend for demo_app
**Labels:** enhancement, good first issue  

The assistant currently runs interactively in CLI mode. A lightweight web UI (e.g., using **Streamlit** or **Gradio**) would make it easier to demo.  
This would be a good enhancement once the docker-in-docker limitation has been handled

Deliverables:  
- Start with a simple input box + output area.  
- Expose the same functionality as the CLI.  

---

### 4. Provide a Helm chart for Kubernetes deployment
**Labels:** enhancement, infra  

Many users may want to deploy on Kubernetes instead of Railway/Render.  

👉 Task: Create a basic Helm chart for deploying `demo_app.py` + MCP server as a service.  

---

### 5. Add GitHub Actions CI/CD pipeline
**Labels:** enhancement, infra  

Set up GitHub Actions to:  
- Run linting + unit tests on PRs.  
- Optionally build and push Docker images to GitHub Container Registry.  

This helps maintain quality and makes the repo production-ready.  

---

### 6. Improve README with usage examples
**Labels:** documentation, good first issue  

The README currently explains setup but lacks examples.  

👉 Add:  
- Example input/output from the assistant.  
- Screenshots of CLI or UI usage (if available).  

---

### 7. Add `.env` file support for configuration
**Labels:** enhancement, good first issue  

Currently, users must export environment variables manually.  

👉 Update the project to support `.env` (via `python-dotenv` or similar), so users can just create a `.env` file like:  

CONFLUENCE_API_KEY=your-key-here
CONFLUENCE_SPACE=your-space

---

## 📚 Documentation

### 8. Add architecture diagram to documentation
**Labels:** documentation  

Add a simple diagram showing how:  
- `demo_app.py`  
- MCP server  
- Confluence API  

fit together.  
This will help new contributors understand the flow faster.  

---

### 9. Expand CONTRIBUTING.md with examples
**Labels:** documentation, good first issue  

Our `CONTRIBUTING.md` exists but is minimal.  

👉 Add:  
- First-time contributor examples (fixing typos, adding test cases).  
- Links to "good first issue" search.  
- Workflow for making PRs.  

---

## 🧪 Testing

### 10. Add unit tests for Confluence API wrapper
**Labels:** testing, good first issue  

Create unit tests that mock API calls to Confluence.  
- Verify that responses are parsed correctly.  
- Test failure cases (invalid space ID, bad auth).  

---

### 11. Add integration test for demo_app workflow
**Labels:** testing  

Add a lightweight integration test:  
- Simulate a small Confluence workspace (mocked).  
- Run demo_app with a sample query.  
- Validate that assistant output matches expectations.  

---

## ✅ Next Steps
- If you’d like to contribute, pick one of the issues above.  
- Check the **labels** (bug, enhancement, documentation, testing) to match your skills.  
- Open an issue in GitHub referencing this file, then submit a PR!  

We welcome all contributions 🙌
