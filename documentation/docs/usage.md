## Usage

### Running the Workflow
Make sure your Docker Desktop app is running.

To run the exploit-and-patch workflow from the command line, navigate to the ``` bountyagent ``` directory and use the following command:
```
python -m workflows.exploit_patch_workflow \
    --task_dir bountybench/setuptools \
    --bounty_number 0 \
    --model anthropic/claude-3-5-sonnet-20240620 \
    --phase_iterations 14
```
Please be aware that there may be a brief delay between initiating the workflow and observing the first log outputs (typically a few seconds). This initial pause is primarily due to the time required for importing necessary Python packages and initializing the environment.

### Running the Application

#### Concurrent run
1. In the root directory run:

```
npm install
npm start
```

This will launch the development server for the frontend and start the backend. You may need to refresh as the backend takes a second to run.

Alternatively you can run the backend and frontend separately as described below.


#### Backend Setup

1. Open a terminal and navigate to the `bountyagent` directory.

2. Start the backend server:
```
python -m backend.main
```
Note: The backend will take about a minute to initialize. You can view incremental, verbose run updates in this terminal window.

#### Frontend Setup

1. Open a new terminal and navigate to the `bountyagent/frontend` directory.

2. If this is your first time running the frontend or if you've updated the project, install the necessary packages:
```
npm install
```
3. After the installation is complete, start the frontend application:
```
npm start
```

This will launch the development server for the frontend.

For a list of API endpoints currently supported, open one of these URLs in your browser:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Accessing the Application

Once both the backend and frontend are running, you can access the application through your web browser (default `localhost:3000`)

### Sample Run
![Screen recording of a run](media/sample_run.gif)

### Troubleshooting

#### Docker Mount Issue

**Error Message:**
Internal Server Error ("Mounts denied: The path *** is not shared from the host and is not known to Docker. You can configure shared paths from Docker -> Preferences... -> Resources -> File Sharing.")

**Solution:**
To resolve this issue, add the absolute path of your `bountyagent` directory to Docker's shared paths. Follow these steps:

1. **Determine the Absolute Path:**
   - Open your terminal.
   - Navigate to the root directory of your project.
   - Retrieve the absolute path using the `pwd` command.
   - **Example Output:**
     ```
     /Users/yourusername/projects/bountyagent
     ```

2. **Add the Path to Docker's Shared Paths:**
   - Open **Docker Desktop** on your machine.
   - Click on the **Settings** (gear) icon.
   - Navigate to **Resources** > **File Sharing**.
   - Paste the absolute path you obtained earlier (e.g., `/Users/yourusername/projects/bountyagent`).
   - Click the **`+`** button to add the new shared path.
   - Also add `/tmp` using the **`+`** button.
   - Click **Apply & Restart** to save the changes.

3. **Verify the Configuration:**
   - After Docker restarts, try running your `bountyagent` workflow again.
   - The error should be resolved, allowing Docker to access the necessary directories.
