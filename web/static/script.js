document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const gameForm = document.getElementById('game-form');
    const fightModeForm = document.getElementById('fight-mode-form');
    const fightModeCheckbox = document.getElementById('fight-mode-checkbox');
    const fightModeSettings = document.getElementById('fight-mode-settings');
    const narratorGroup = document.getElementById('narrator-group');
    const detectiveGroup = document.getElementById('detective-group');
    const startGameBtn = document.getElementById('start-game-btn');
    const startFightBtn = document.getElementById('start-fight-btn');
    const chatContainer = document.getElementById('chat-container');
    const typingIndicator = document.getElementById('typing-indicator');
    const sessionTitle = document.getElementById('session-title');
    const statusBadge = document.getElementById('status-badge');
    const saveBtn = document.getElementById('save-btn');

    // State
    let isFightMode = false;
    let isGameRunning = false;
    let mysteryShown = false; // Track if the mystery has been shown

    // Event Listeners
    fightModeCheckbox.addEventListener('change', toggleFightMode);
    startGameBtn.addEventListener('click', () => startGame());
    startFightBtn.addEventListener('click', () => startFight());
    saveBtn.addEventListener('click', saveConversation);

    // Toggle Fight Mode
    function toggleFightMode() {
        isFightMode = fightModeCheckbox.checked;

        if (isFightMode) {
            fightModeSettings.classList.remove('hidden');
            narratorGroup.classList.remove('hidden'); // Narrator is used in both
            detectiveGroup.classList.add('hidden'); // Single detective hidden in fight mode
            startGameBtn.classList.add('hidden');
            startFightBtn.classList.remove('hidden');
            sessionTitle.textContent = "Fight Mode Session";
        } else {
            fightModeSettings.classList.add('hidden');
            narratorGroup.classList.remove('hidden');
            detectiveGroup.classList.remove('hidden');
            startGameBtn.classList.remove('hidden');
            startFightBtn.classList.add('hidden');
            sessionTitle.textContent = "Single Player Session";
        }
    }

    // Helper: Add Message to Chat
    function addMessage(content, type, senderName = null) {
        const messageRow = document.createElement('div');
        messageRow.classList.add('message-row', type);

        const bubble = document.createElement('div');
        bubble.classList.add('message-bubble');

        if (type === 'mystery') {
            bubble.classList.add('mystery-bubble');
            senderName = 'Misterio';
        } else if (type === 'narrator') {
            bubble.classList.add('narrator-bubble');
            senderName = senderName || 'Narrador';
        } else if (type === 'detective') {
            bubble.classList.add('detective-bubble');
            senderName = senderName || 'Detective';
        } else if (type === 'detective2') { // Custom type for 2nd detective
            bubble.classList.add('detective2-bubble');
            senderName = senderName || 'Detective 2';
            messageRow.classList.add('detective'); // Align right like detective 1
        } else if (type === 'system') {
            bubble.classList.add('system-message');
        } else if (type === 'error') {
            bubble.classList.add('error-message');
        }

        if (senderName && type !== 'system' && type !== 'error') {
            const nameSpan = document.createElement('span');
            nameSpan.classList.add('sender-name');
            nameSpan.textContent = senderName;
            bubble.appendChild(nameSpan);
        }

        // Handle HTML content for summary or plain text for messages
        if (type === 'summary') {
            bubble.innerHTML = content; // Allow HTML for summary
            bubble.classList.add('fight-summary'); // Special styling
            messageRow.classList.add('system'); // Center align
        } else {
            const textNode = document.createTextNode(content);
            bubble.appendChild(textNode);
        }

        messageRow.appendChild(bubble);
        chatContainer.appendChild(messageRow);
        scrollToBottom();
    }

    // Helper: Scroll to Bottom
    function scrollToBottom() {
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    // Helper: Set Loading State
    function setLoading(loading) {
        isGameRunning = loading;
        startGameBtn.disabled = loading;
        startFightBtn.disabled = loading;

        if (loading) {
            typingIndicator.classList.remove('hidden');
            statusBadge.textContent = "Running...";
            statusBadge.className = "status-badge active";
            saveBtn.disabled = true;
        } else {
            typingIndicator.classList.add('hidden');
            statusBadge.textContent = "Completed";
            statusBadge.className = "status-badge ready";
            saveBtn.disabled = false;
        }
        scrollToBottom();
    }

    // Start Single Player Game
    async function startGame() {
        if (isGameRunning) return;

        // Clear chat and reset mystery flag
        chatContainer.innerHTML = '';
        mysteryShown = false;
        addMessage("Starting new game session...", "system");
        setLoading(true);

        const formData = new FormData(gameForm);
        const data = Object.fromEntries(formData.entries());

        try {
            const response = await fetch('/start_game', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            await processStream(reader, decoder, (line) => {
                if (!line.trim()) return;

                // Simple parsing logic based on prefixes
                if (line.startsWith('Narrator:')) {
                    const content = line.replace('Narrator:', '').trim();
                    // First narrator message is the mystery
                    if (!mysteryShown) {
                        addMessage(content, 'mystery');
                        mysteryShown = true;
                    } else {
                        addMessage(content, 'narrator');
                    }
                } else if (line.startsWith('Detective:')) {
                    addMessage(line.replace('Detective:', '').trim(), 'detective');
                } else if (line.startsWith('Error')) {
                    addMessage(line, 'error');
                } else if (line === 'save_conversation') {
                    // Ignore, handled by UI state
                } else {
                    // Treat everything else as system/event messages
                    // Filter out some internal debug lines if needed
                    if (!line.startsWith('DEBUG:')) {
                        addMessage(line, 'system');
                    }
                }
            });
        } catch (error) {
            addMessage(`Connection error: ${error.message}`, 'error');
        } finally {
            setLoading(false);
        }
    }

    // Start Fight Mode
    async function startFight() {
        if (isGameRunning) return;

        chatContainer.innerHTML = '';
        mysteryShown = false;
        addMessage("Starting fight mode session...", "system");
        setLoading(true);

        const gameFormData = new FormData(gameForm);
        const fightFormData = new FormData(fightModeForm);

        const data = {
            ...Object.fromEntries(fightFormData.entries()),
            narrator_model: gameFormData.get('narrator_model'),
            difficulty: gameFormData.get('difficulty')
        };

        try {
            const response = await fetch('/start_fight', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            await processStream(reader, decoder, (line) => {
                if (!line.trim()) return;

                try {
                    const msg = JSON.parse(line);

                    if (msg.type === 'narrator') {
                        // First narrator message is the mystery
                        if (!mysteryShown) {
                            addMessage(msg.content, 'mystery');
                            mysteryShown = true;
                        } else {
                            addMessage(msg.content, 'narrator');
                        }
                    } else if (msg.type.includes('detective1')) {
                        // Extract content, remove prefixes if present
                        let content = msg.content.replace(/^Detective 1 (pregunta|dice):/, '').trim();
                        addMessage(content, 'detective', 'Detective 1');
                    } else if (msg.type.includes('detective2')) {
                        let content = msg.content.replace(/^Detective 2 (pregunta|dice):/, '').trim();
                        addMessage(content, 'detective2', 'Detective 2');
                    } else if (msg.type === 'summary') {
                        addMessage(msg.content, 'summary');
                    } else if (msg.type === 'error') {
                        addMessage(msg.content, 'error');
                    } else {
                        addMessage(msg.content, 'system');
                    }
                } catch (e) {
                    console.error("JSON Parse Error:", e, line);
                    // Fallback for non-JSON lines
                    addMessage(line, 'system');
                }
            });
        } catch (error) {
            addMessage(`Connection error: ${error.message}`, 'error');
        } finally {
            setLoading(false);
        }
    }

    // Process Stream Helper
    async function processStream(reader, decoder, callback) {
        let buffer = '';
        while (true) {
            const { done, value } = await reader.read();
            if (done) {
                if (buffer) callback(buffer);
                break;
            }
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop();

            for (const line of lines) {
                callback(line);
            }
        }
    }

    // Save Conversation
    async function saveConversation() {
        try {
            const response = await fetch('/save_conversation', { method: 'POST' });
            const result = await response.json();
            if (response.ok) {
                alert('Conversation saved successfully!');
            } else {
                alert(`Error saving: ${result.message}`);
            }
        } catch (error) {
            alert(`Network error: ${error.message}`);
        }
    }
});
