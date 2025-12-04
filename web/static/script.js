document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const gameForm = document.getElementById('game-form');
    const fightModeForm = document.getElementById('fight-mode-form');
    const councilModeForm = document.getElementById('council-mode-form');

    const gameModeSelect = document.getElementById('game-mode');

    const singleModeSettings = document.getElementById('single-mode-settings');
    const fightModeSettings = document.getElementById('fight-mode-settings');
    const councilModeSettings = document.getElementById('council-mode-settings');
    const inverseModeSettings = document.getElementById('inverse-mode-settings');
    const inverseControls = document.getElementById('inverse-controls');

    const narratorGroup = document.getElementById('narrator-group');
    const detectiveGroup = document.getElementById('detective-group');

    const startGameBtn = document.getElementById('start-game-btn');
    const chatContainer = document.getElementById('chat-container');
    const typingIndicator = document.getElementById('typing-indicator');
    const sessionTitle = document.getElementById('session-title');
    const statusBadge = document.getElementById('status-badge');
    const saveBtn = document.getElementById('save-btn');
    const hintBtn = document.getElementById('hint-btn');

    const chatInputArea = document.getElementById('chat-input-area');
    const userInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    const solveBtn = document.getElementById('solve-btn');

    // State
    let currentMode = 'single'; // 'single', 'fight', 'council'
    let isGameRunning = false;
    let mysteryShown = false; // Track if the mystery has been shown
    let sessionId = null; // Store the unique session ID

    // Initialize Session ID
    function initSession() {
        sessionId = localStorage.getItem('blackstory_session_id');
        if (!sessionId) {
            sessionId = crypto.randomUUID();
            localStorage.setItem('blackstory_session_id', sessionId);
        }
        console.log("Session ID:", sessionId);
    }

    initSession();

    // Event Listeners
    gameModeSelect.addEventListener('change', handleModeChange);
    startGameBtn.addEventListener('click', () => handleStartGame());
    startGameBtn.addEventListener('click', () => handleStartGame());
    saveBtn.addEventListener('click', saveConversation);
    hintBtn.addEventListener('click', requestHint);

    sendBtn.addEventListener('click', sendMessage);
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });
    solveBtn.addEventListener('click', solveMystery);

    // Inverse Mode Buttons
    document.querySelectorAll('.btn-inverse').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const answer = e.target.dataset.answer;
            handleInverseAnswer(answer);
        });
    });

    // Handle Mode Change
    function handleModeChange() {
        currentMode = gameModeSelect.value;

        // Reset visibility
        singleModeSettings.classList.add('hidden');
        fightModeSettings.classList.add('hidden');
        councilModeSettings.classList.add('hidden');
        inverseModeSettings.classList.add('hidden');
        detectiveGroup.classList.add('hidden'); // Default hidden, shown only in single
        hintBtn.classList.add('hidden');
        chatInputArea.classList.add('hidden');
        inverseControls.classList.add('hidden');

        if (currentMode === 'single') {
            singleModeSettings.classList.remove('hidden');
            detectiveGroup.classList.remove('hidden');
            sessionTitle.textContent = "Single Player Session";
            startGameBtn.textContent = "Start Game";
            startGameBtn.className = "btn btn-primary";
        } else if (currentMode === 'interactive') {
            singleModeSettings.classList.remove('hidden'); // Reuse single settings for narrator model
            // Hide detective model input since user is detective
            detectiveGroup.classList.add('hidden');
            sessionTitle.textContent = "Interactive Session";
            startGameBtn.textContent = "Start Interactive Game";
            startGameBtn.className = "btn btn-primary";
            hintBtn.classList.remove('hidden');
        } else if (currentMode === 'fight') {
            fightModeSettings.classList.remove('hidden');
            sessionTitle.textContent = "Fight Mode Session";
            startGameBtn.textContent = "Start Fight";
            startGameBtn.className = "btn btn-danger";
        } else if (currentMode === 'council') {
            councilModeSettings.classList.remove('hidden');
            sessionTitle.textContent = "Council Mode Session";
            startGameBtn.textContent = "Start Council";
            startGameBtn.className = "btn btn-warning"; // Use a distinct color if available, or custom class
            startGameBtn.style.backgroundColor = "#f59e0b"; // Manual override for now
        } else if (currentMode === 'inverse') {
            inverseModeSettings.classList.remove('hidden');
            sessionTitle.textContent = "Inverse Mode (You are Narrator)";
            startGameBtn.textContent = "Start Inverse Game";
            startGameBtn.className = "btn btn-info"; // Distinct color
            startGameBtn.style.backgroundColor = "#8b5cf6"; // Violet
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
        } else if (type === 'detective2') {
            bubble.classList.add('detective2-bubble');
            senderName = senderName || 'Detective 2';
            messageRow.classList.add('detective');
        } else if (type === 'council_visionary') {
            bubble.classList.add('visionary-bubble');
            bubble.style.backgroundColor = '#e0f2fe'; // Light blue
            bubble.style.color = '#0369a1';
            senderName = 'Visionario';
            messageRow.classList.add('system'); // Center align or distinct
        } else if (type === 'council_skeptic') {
            bubble.classList.add('skeptic-bubble');
            bubble.style.backgroundColor = '#fef2f2'; // Light red
            bubble.style.color = '#b91c1c';
            senderName = 'Escéptico';
            messageRow.classList.add('system');
        } else if (type === 'council_leader') {
            bubble.classList.add('leader-bubble');
            bubble.style.backgroundColor = '#f0fdf4'; // Light green
            bubble.style.color = '#15803d';
            senderName = 'Líder';
            messageRow.classList.add('detective'); // Align right
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
            bubble.innerHTML = content;
            bubble.classList.add('fight-summary');
            messageRow.classList.add('system');
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

        if (loading) {
            typingIndicator.classList.remove('hidden');
            statusBadge.textContent = "Running...";
            statusBadge.className = "status-badge active";
            saveBtn.disabled = true;
            if (currentMode === 'single') {
                // No hint button in single player (AI vs AI)
            }
            if (currentMode === 'interactive') {
                hintBtn.classList.remove('hidden');
                hintBtn.disabled = false;
            }
        } else {
            typingIndicator.classList.add('hidden');
            statusBadge.textContent = "Completed";
            statusBadge.className = "status-badge ready";
            saveBtn.disabled = false;

            if (currentMode === 'interactive') {
                hintBtn.classList.remove('hidden');
                hintBtn.disabled = false;
            } else {
                hintBtn.classList.add('hidden');
                hintBtn.disabled = true;
            }
        }
        scrollToBottom();
    }

    // Main Start Handler
    function handleStartGame() {
        if (isGameRunning) return;

        if (currentMode === 'single') {
            startSingleGame();
        } else if (currentMode === 'interactive') {
            startInteractiveGame();
        } else if (currentMode === 'fight') {
            startFightGame();
        } else if (currentMode === 'council') {
            startCouncilGame();
        } else if (currentMode === 'inverse') {
            startInverseGame();
        }
    }

    // Start Single Player Game
    async function startSingleGame() {
        chatContainer.innerHTML = '';
        mysteryShown = false;
        addMessage("Starting new game session...", "system");
        setLoading(true);

        const formData = new FormData(gameForm);
        const data = Object.fromEntries(formData.entries());
        data.session_id = sessionId;

        // Manually add detective_model since it's outside the main form
        const detectiveModelInput = document.getElementById('detective-model');
        if (detectiveModelInput) {
            data.detective_model = detectiveModelInput.value;
        }

        try {
            const response = await fetch('/start_game', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            await handleStreamResponse(response);
        } catch (error) {
            addMessage(`Connection error: ${error.message}`, 'error');
        } finally {
            setLoading(false);
        }
    }

    // Start Interactive Game
    async function startInteractiveGame() {
        chatContainer.innerHTML = '';
        mysteryShown = false;
        addMessage("Starting interactive session...", "system");
        setLoading(true);
        chatInputArea.classList.add('hidden'); // Hide input during setup

        const formData = new FormData(gameForm);
        const data = Object.fromEntries(formData.entries());
        data.session_id = sessionId;

        try {
            const response = await fetch('/start_interactive', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            await handleStreamResponse(response);
        } catch (error) {
            addMessage(`Connection error: ${error.message}`, 'error');
            setLoading(false);
        }
        // Note: setLoading(false) is NOT called here because we want to stay "active" 
        // but we need to switch to "waiting for user" state.
        // The stream will send a specific message when ready.
    }

    // Start Fight Mode
    async function startFightGame() {
        chatContainer.innerHTML = '';
        mysteryShown = false;
        addMessage("Starting fight mode session...", "system");
        setLoading(true);

        const gameFormData = new FormData(gameForm);
        const fightFormData = new FormData(fightModeForm);

        const data = {
            ...Object.fromEntries(fightFormData.entries()),
            narrator_model: gameFormData.get('narrator_model'),
            difficulty: gameFormData.get('difficulty'),
            session_id: sessionId
        };

        try {
            const response = await fetch('/start_fight', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            await handleStreamResponse(response);
        } catch (error) {
            addMessage(`Connection error: ${error.message}`, 'error');
        } finally {
            setLoading(false);
        }
    }

    // Start Council Mode
    async function startCouncilGame() {
        chatContainer.innerHTML = '';
        mysteryShown = false;
        addMessage("Convoking the Council of Detectives...", "system");
        setLoading(true);

        const gameFormData = new FormData(gameForm);
        const councilFormData = new FormData(councilModeForm);

        const data = {
            ...Object.fromEntries(councilFormData.entries()),
            narrator_model: gameFormData.get('narrator_model'),
            difficulty: gameFormData.get('difficulty'),
            session_id: sessionId
        };

        try {
            const response = await fetch('/start_council', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            await handleStreamResponse(response);
        } catch (error) {
            addMessage(`Connection error: ${error.message}`, 'error');
        } finally {
            setLoading(false);
        }
    }

    // Start Inverse Game
    async function startInverseGame() {
        chatContainer.innerHTML = '';
        mysteryShown = false;
        addMessage("Initializing Inverse Mode...", "system");
        setLoading(true);
        inverseControls.classList.add('hidden');

        const gameFormData = new FormData(gameForm);
        const inverseDetectiveModel = document.getElementById('inverse-detective-model').value;

        const data = {
            difficulty: gameFormData.get('difficulty'),
            detective_model: inverseDetectiveModel,
            session_id: sessionId
        };

        try {
            const response = await fetch('/start_inverse', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            await handleStreamResponse(response);
        } catch (error) {
            addMessage(`Connection error: ${error.message}`, 'error');
            setLoading(false);
        }
    }

    // Generic Stream Handler
    async function handleStreamResponse(response) {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        await processStream(reader, decoder, (line) => {
            if (!line.trim()) return;

            try {
                // Try parsing as JSON first (used by Fight and Council modes)
                if (line.startsWith('{')) {
                    const msg = JSON.parse(line);
                    handleJsonMessage(msg);
                } else {
                    // Fallback for Single Player legacy format
                    handleLegacyMessage(line);
                }
            } catch (e) {
                console.error("Parse Error:", e, line);
                addMessage(line, 'system');
            }
        });
    }

    function handleJsonMessage(msg) {
        if (msg.type === 'narrator') {
            if (!mysteryShown) {
                addMessage(msg.content, 'mystery');
                mysteryShown = true;
            } else {
                addMessage(msg.content, 'narrator');
            }
        } else if (msg.type.includes('detective1')) {
            let content = msg.content.replace(/^Detective 1 (pregunta|dice):/, '').trim();
            addMessage(content, 'detective', 'Detective 1');
        } else if (msg.type.includes('detective2')) {
            let content = msg.content.replace(/^Detective 2 (pregunta|dice):/, '').trim();
            addMessage(content, 'detective2', 'Detective 2');
        } else if (msg.type === 'council_visionary') {
            addMessage(msg.content, 'council_visionary');
        } else if (msg.type === 'council_skeptic') {
            addMessage(msg.content, 'council_skeptic');
        } else if (msg.type === 'council_leader') {
            addMessage(msg.content, 'council_leader');
        } else if (msg.type === 'summary') {
            addMessage(msg.content, 'summary');
        } else if (msg.type === 'error') {
            addMessage(msg.content, 'error');
        } else if (msg.type === 'interactive_ready') {
            addMessage(msg.content, 'system');
            setLoading(false); // Stop "loading" animation
            isGameRunning = true; // But game is still logically running
            statusBadge.textContent = "Your Turn";
            chatInputArea.classList.remove('hidden');
            userInput.focus();
        } else if (msg.type === 'inverse_init') {
            addMessage(`Misterio: ${msg.mystery}`, 'mystery');
            addMessage(`Solución (SOLO PARA TI): ${msg.solution}`, 'system');
            mysteryShown = true;
            setLoading(false);
            isGameRunning = true;
            statusBadge.textContent = "Your Turn (Narrator)";
        } else if (msg.type === 'inverse_question') {
            addMessage(msg.content, 'detective');
            // Show controls for user to answer
            inverseControls.classList.remove('hidden');
            // Scroll to bottom to ensure controls are seen
            setTimeout(scrollToBottom, 100);
        } else if (msg.type === 'inverse_solution') {
            // The content is already added as a message by the engine
            inverseControls.classList.remove('hidden');
            setTimeout(scrollToBottom, 100);
        } else if (msg.type === 'status') {
            // Just a status update
        } else {
            addMessage(msg.content, 'system');
        }
    }

    function handleLegacyMessage(line) {
        if (line.startsWith('Narrator:')) {
            const content = line.replace('Narrator:', '').trim();
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
            // Ignore
        } else {
            if (!line.startsWith('DEBUG:')) {
                addMessage(line, 'system');
            }
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
            const response = await fetch('/save_conversation', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ session_id: sessionId })
            });
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



    // Request Hint
    async function requestHint() {
        hintBtn.disabled = true;
        addMessage("Solicitando pista a Watson...", "system");

        try {
            const response = await fetch('/get_hint', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ session_id: sessionId })
            });
            const result = await response.json();

            if (response.ok) {
                addMessage(`💡 Pista de Watson: ${result.hint}`, 'system');
            } else {
                addMessage(`Error obteniendo pista: ${result.message}`, 'error');
            }
        } catch (error) {
            addMessage(`Error de red: ${error.message}`, 'error');
        } finally {
            if (isGameRunning) {
                hintBtn.disabled = false;
            }
        }
    }

    // Send Message (Interactive Mode)
    async function sendMessage() {
        const text = userInput.value.trim();
        if (!text) return;

        addMessage(text, 'detective', 'Tú');
        userInput.value = '';
        userInput.disabled = true;
        sendBtn.disabled = true;

        // Show typing indicator
        typingIndicator.classList.remove('hidden');

        try {
            const response = await fetch('/ask_narrator', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ session_id: sessionId, question: text })
            });
            const result = await response.json();

            if (response.ok) {
                addMessage(result.answer, 'narrator');
            } else {
                addMessage(`Error: ${result.message}`, 'error');
            }
        } catch (error) {
            addMessage(`Network error: ${error.message}`, 'error');
        } finally {
            userInput.disabled = false;
            sendBtn.disabled = false;
            typingIndicator.classList.add('hidden');
            userInput.focus();
        }
    }

    // Handle Inverse Answer
    async function handleInverseAnswer(answer) {
        // Hide controls immediately to prevent double clicks
        inverseControls.classList.add('hidden');
        addMessage(answer, 'narrator', 'Tú');

        try {
            const response = await fetch('/inverse_answer', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ session_id: sessionId, answer: answer })
            });
            await handleStreamResponse(response);
        } catch (error) {
            addMessage(`Connection error: ${error.message}`, 'error');
            // Show controls again if error?
            inverseControls.classList.remove('hidden');
        }
    }

    // Solve Mystery (Interactive Mode)
    async function solveMystery() {
        const solution = prompt("Por favor, introduce tu solución final al misterio:");
        if (!solution) return;

        addMessage(`Solución propuesta: ${solution}`, 'detective', 'Tú');
        chatInputArea.classList.add('hidden'); // Hide input area
        setLoading(true); // Show loading state

        try {
            const response = await fetch('/solve_mystery', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ session_id: sessionId, solution: solution })
            });
            await handleStreamResponse(response);
        } catch (error) {
            addMessage(`Connection error: ${error.message}`, 'error');
        } finally {
            setLoading(false);
        }
    }

    // Initial UI Setup
    handleModeChange(); // Set initial state
});
