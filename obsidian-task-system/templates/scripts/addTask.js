async function addTask(tp) {
  // Prompt for the task name
  const taskName = await tp.system.prompt("New task:");
  if (!taskName) return "";

  // Prompt for which lane (default: Backlog)
  const lane = await tp.system.suggester(
    ["📋 Backlog", "🎯 Today", "⏳ Waiting On"],
    ["Backlog", "Today", "Waiting On"],
    false,
    "Add to which column?"
  );
  if (!lane) return "";

  // Build the task note content
  const today = tp.date.now("YYYY-MM-DD");
  const noteContent = `---\ntags: [task]\nstatus: ${lane === "Today" ? "today" : lane === "Waiting On" ? "waiting" : "backlog"}\ncreated: "${today}"\ndue: \nwaiting_on: \npriority: \n---\n\n# ${taskName}\n\n`;

  // Create the note in tasks/
  const fileName = `tasks/${taskName}`;
  try {
    const file = await tp.file.create_new(noteContent, fileName);
  } catch (e) {
    // File might already exist
    new Notice(`Note "${taskName}" may already exist in tasks/`);
  }

  // Add the card to the Tasks Board
  const boardPath = "Tasks Board.md";
  const boardFile = tp.file.find_tfile(boardPath);
  if (boardFile) {
    let content = await app.vault.read(boardFile);

    // Find the right lane header and insert after it
    let laneHeader;
    if (lane === "Today") laneHeader = "## 🎯 Today";
    else if (lane === "Waiting On") laneHeader = "## ⏳ Waiting On";
    else laneHeader = "## 📋 Backlog";

    const headerIndex = content.indexOf(laneHeader);
    if (headerIndex !== -1) {
      // Find the end of the header line
      const afterHeader = content.indexOf("\n", headerIndex) + 1;
      // Insert the new card right after the header
      const newCard = `- [ ] [[${taskName}]]\n`;
      content = content.slice(0, afterHeader) + "\n" + newCard + content.slice(afterHeader);
      await app.vault.modify(boardFile, content);
    }
  }

  new Notice(`✅ Added "${taskName}" to ${lane}`);
  return "";
}

module.exports = addTask;
