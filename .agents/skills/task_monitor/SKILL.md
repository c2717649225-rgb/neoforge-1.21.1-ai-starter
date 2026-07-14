---
name: task_monitor
description: >
  [按需·非默认] 编译超时监控辅助，仅在进行长 Gradle/Git 命令需后台防假死监控时使用。
---

> **[方案二 · 按需]**
> 本 skill **不是**默认开发路径的一部分。
> Minor / 编译修复 / 概念问答：**不要**加载本 skill。
> 仅在用户要求或 Major 且本步骤需要时使用。

# Background Task Monitor Skill

This skill provides guidelines and procedures to automatically monitor long-running background tasks launched via the shell command execution tool. It ensures that tasks do not hang indefinitely and that you proactively recover from connection timeouts or permission blocks.

## 1. Trigger Criteria & Mandatory Action
Whenever you start a background task (e.g., download, git clone, build, compilation) that returns a Task ID, you **MUST** immediately schedule a one-shot check timer using the timer/scheduler tool before ending your turn:
- Set duration to `60` seconds
- Prompt: `"Check the status of background task <TaskId>"`

---

## 2. Monitoring & Diagnostic Procedure
When the 60-second timer triggers (or you are woken up by a message), perform the following checks:

### Step A: Query Task Status
Call the task management tool with Action="status" and TaskId="<TaskId>".

### Step B: Analyze the Task State
1. **If the task is finished successfully**:
   - Proceed with your next step or report completion.
2. **If the task has failed**:
   - Read the log file or stderr, diagnose the issue (e.g., TLS error, bad URL, out of memory), and run a corrective action or report back with a fix.
3. **If the task is still `RUNNING`**:
   - Check the log output returned in the status response.
   - If the log output shows no new progress since the last check, or if it is stuck on commands known to block (like raw `git clone` on blocked domains, `git ls-remote`, credential prompts, or downloading from slow CDNs):
     - **It is considered STUCK.** Proceed to **Section 3: Corrective Actions**.
   - If the log output shows active progress (file sizes increasing, files compiling):
      - Schedule another 60-second timer using the timer/scheduler facility and stop calling tools.

---

## 3. Corrective Actions for Stuck Tasks
If you determine a task is stuck or failing, you must intervene immediately:
1. **Kill the Stuck Task**: Call the task management tool with Action="kill".
2. **Determine the Root Cause & Apply Fallbacks**:
   - **Network Timeout / Git Clone Hang**: 
     - Switch to using a fast mirror (e.g., `mirror.ghproxy.com`, `ghproxy.net` or `github.moeyy.xyz`).
     - **Prefer ZIP downloads**: Instead of `git clone`, download the repository ZIP file from the mirror using `curl.exe` with a strict connection timeout (e.g., `--connect-timeout 10 --max-time 180`) and extract it. This completely avoids protocol hangs.
   - **Gradle Sync Hang**:
     - Check if the Gradle wrapper is stuck downloading. Check if you need to inject mirror configurations (like Aliyun Maven mirror) into `build.gradle` or setup local proxies in `gradle.properties`.
3. **Restart**: Launch the corrected command and set a new 60-second check timer.
