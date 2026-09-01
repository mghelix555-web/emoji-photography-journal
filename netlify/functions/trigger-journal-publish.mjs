const workflowDispatchUrl =
  "https://api.github.com/repos/mghelix555-web/emoji-photography-journal/actions/workflows/publish-scheduled-posts.yml/dispatches";

export const config = {
  schedule: "5 12 * * *",
};

export default async () => {
  const token = process.env.JOURNAL_GITHUB_TOKEN;

  if (!token) {
    const message =
      "JOURNAL_GITHUB_TOKEN is missing; unable to dispatch the journal publishing workflow.";
    console.error(message);
    throw new Error(message);
  }

  const response = await fetch(workflowDispatchUrl, {
    method: "POST",
    headers: {
      Accept: "application/vnd.github+json",
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
      "X-GitHub-Api-Version": "2026-03-10",
    },
    body: JSON.stringify({ ref: "main" }),
  });

  if (!response.ok) {
    const responseBody = await response.text();
    console.error(
      `GitHub workflow dispatch failed with HTTP ${response.status}: ${responseBody}`,
    );
    throw new Error(
      `GitHub workflow dispatch failed with HTTP ${response.status}.`,
    );
  }

  console.log("GitHub workflow dispatch succeeded for ref main.");
};
