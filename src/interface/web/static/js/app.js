/**
 * Main JavaScript file for the Messenger App
 */

// Authentication helper functions
const auth = {
    // Get stored token
    getToken: function() {
        return localStorage.getItem('token');
    },
    
    // Save token to local storage and cookies for server-side auth
    setToken: function(token) {
        localStorage.setItem('token', token);
        
        // Also set cookie for server-side auth
        this.setCookie('token', token, 7); // 7 days
    },
    
    // Remove token (logout)
    removeToken: function() {
        localStorage.removeItem('token');
        this.deleteCookie('token');
    },
    
    // Check if user is logged in
    isLoggedIn: function() {
        return !!this.getToken();
    },
    
    // Add token to request headers
    getAuthHeaders: function() {
        const token = this.getToken();
        return token ? { 'Authorization': `Bearer ${token}` } : {};
    },
    
    // Cookie helpers
    setCookie: function(name, value, days) {
        let expires = '';
        if (days) {
            const date = new Date();
            date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
            expires = '; expires=' + date.toUTCString();
        }
        document.cookie = name + '=' + (value || '') + expires + '; path=/';
    },
    
    getCookie: function(name) {
        const nameEQ = name + '=';
        const ca = document.cookie.split(';');
        for (let i = 0; i < ca.length; i++) {
            let c = ca[i];
            while (c.charAt(0) === ' ') c = c.substring(1, c.length);
            if (c.indexOf(nameEQ) === 0) return c.substring(nameEQ.length, c.length);
        }
        return null;
    },
    
    deleteCookie: function(name) {
        document.cookie = name + '=; Max-Age=-99999999; path=/';
    }
};

// API wrapper
const api = {
    // Base API URL
    baseUrl: '/api',
    
    // Make authenticated API request
    async request(method, endpoint, data = null) {
        const url = `${this.baseUrl}${endpoint}`;
        const headers = {
            'Content-Type': 'application/json',
            ...auth.getAuthHeaders()
        };
        
        const options = {
            method,
            headers,
            credentials: 'include', // Include cookies
        };
        
        if (data && (method === 'POST' || method === 'PUT' || method === 'PATCH')) {
            options.body = JSON.stringify(data);
        }
        
        try {
            const response = await fetch(url, options);
            
            // Handle unauthorized errors
            if (response.status === 401) {
                auth.removeToken();
                window.location.href = '/web/login';
                return null;
            }
            
            // Parse JSON response
            if (response.status !== 204) { // No content
                const result = await response.json();
                return { success: response.ok, data: result, status: response.status };
            }
            
            return { success: response.ok, status: response.status };
        } catch (error) {
            console.error('API request error:', error);
            return { success: false, error: error.message };
        }
    },
    
    // Convenience methods
    async get(endpoint) {
        return this.request('GET', endpoint);
    },
    
    async post(endpoint, data) {
        return this.request('POST', endpoint, data);
    },
    
    async put(endpoint, data) {
        return this.request('PUT', endpoint, data);
    },
    
    async delete(endpoint) {
        return this.request('DELETE', endpoint);
    }
};

// WebSocket client
const wsClient = {
    // WebSocket connection
    socket: null,
    
    // Connection status
    connected: false,
    
    // Message handlers
    messageHandlers: {},
    
    // Connect to WebSocket server
    connect() {
        if (this.socket) {
            // Already connected or connecting
            return;
        }
        
        const token = auth.getToken();
        if (!token) {
            console.error('Cannot connect to WebSocket: No auth token');
            return;
        }
        
        // Determine WebSocket URL (ws or wss based on current protocol)
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        const wsUrl = `${protocol}//${host}/ws`;
        
        try {
            // Need to use the WebSocket protocols parameter for header-like authentication
            // since WebSocket API doesn't directly support custom headers
            this.socket = new WebSocket(wsUrl, ["access_token", token]);
            // Setup event handlers
            this.socket.onopen = () => {
                console.log('WebSocket connected');
                this.connected = true;
                this.triggerHandler('connect');
            };
            
            this.socket.onclose = (event) => {
                console.log('WebSocket disconnected', event.code, event.reason);
                this.connected = false;
                this.socket = null;
                this.triggerHandler('disconnect', { code: event.code, reason: event.reason });
                
                // Try to reconnect after delay if it wasn't a purposeful disconnection
                if (event.code !== 1000) {
                    setTimeout(() => this.connect(), 5000);
                }
            };
            
            this.socket.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.triggerHandler('error', error);
            };
            
            this.socket.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);
                    console.log('WebSocket message received:', message);
                    
                    // Call specific handler based on message type
                    this.triggerHandler(message.type, message);
                    
                    // Also trigger generic message handler
                    this.triggerHandler('message', message);
                } catch (error) {
                    console.error('Error parsing WebSocket message:', error, event.data);
                }
            };
        } catch (error) {
            console.error('Error creating WebSocket connection:', error);
        }
    },
    
    // Disconnect from WebSocket server
    disconnect() {
        if (this.socket) {
            this.socket.close(1000, 'User disconnected');
            this.socket = null;
            this.connected = false;
        }
    },
    
    // Send message to WebSocket server
    send(message) {
        if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
            console.error('Cannot send message: WebSocket not connected');
            return false;
        }
        
        try {
            this.socket.send(JSON.stringify(message));
            return true;
        } catch (error) {
            console.error('Error sending WebSocket message:', error);
            return false;
        }
    },
    
    // Send chat message
    sendChatMessage(chatId, content) {
        return this.send({
            type: 'chat',
            chat_id: chatId,
            content: content
        });
    },
    
    // Send typing notification
    sendTypingStatus(chatId, isTyping) {
        return this.send({
            type: 'typing',
            chat_id: chatId,
            is_typing: isTyping
        });
    },
    
    // Send read receipt
    sendReadReceipt(messageId) {
        return this.send({
            type: 'read',
            message_id: messageId
        });
    },
    
    // Register message handler
    on(type, handler) {
        if (!this.messageHandlers[type]) {
            this.messageHandlers[type] = [];
        }
        this.messageHandlers[type].push(handler);
    },
    
    // Remove message handler
    off(type, handler) {
        if (!this.messageHandlers[type]) return;
        
        if (handler) {
            // Remove specific handler
            const index = this.messageHandlers[type].indexOf(handler);
            if (index !== -1) {
                this.messageHandlers[type].splice(index, 1);
            }
        } else {
            // Remove all handlers for this type
            this.messageHandlers[type] = [];
        }
    },
    
    // Trigger handlers for a message type
    triggerHandler(type, data) {
        const handlers = this.messageHandlers[type] || [];
        for (const handler of handlers) {
            try {
                handler(data);
            } catch (error) {
                console.error(`Error in WebSocket ${type} handler:`, error);
            }
        }
    }
};

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize logout functionality
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', function() {
            // Disconnect WebSocket before logout
            wsClient.disconnect();
            auth.removeToken();
            window.location.href = '/web/login';
        });
    }
    
    // Initialize login form handling
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            
            try {
                // FastAPI's OAuth2 uses form data rather than JSON for login
                const formData = new URLSearchParams();
                formData.append('username', username);
                formData.append('password', password);
                
                const loginUrl = `${api.baseUrl}/auth/login`;
                const loginResponse = await fetch(loginUrl, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                    },
                    body: formData,
                    credentials: 'include'
                });
                
                const response = await loginResponse.json();
                response.success = loginResponse.ok;
                
                if (response && response.success) {
                    auth.setToken(response.access_token);
                    window.location.href = '/web/dashboard';
                } else {
                    alert('Login failed: ' + (response?.data?.detail || 'Unknown error'));
                }
            } catch (error) {
                alert('Login error: ' + error.message);
            }
        });
    }
    
    // Initialize register form handling
    const registerForm = document.getElementById('register-form');
    if (registerForm) {
        registerForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            const name = document.getElementById('name').value || '';
            const username = document.getElementById('username').value;
            const phone = document.getElementById('phone').value || '';
            const password = document.getElementById('password').value;
            
            try {
                const response = await api.post('/auth/register', { 
                    username, 
                    password,
                    name,
                    phone
                });
                
                if (response && response.success) {
                    alert('Registration successful! Please login.');
                    window.location.href = '/web/login';
                } else {
                    alert('Registration failed: ' + (response?.data?.detail || 'Unknown error'));
                }
            } catch (error) {
                alert('Registration error: ' + error.message);
            }
        });
    }
    
    // Initialize chat functionality
    initChatFunctionality();
    
    // Connect to WebSocket if user is logged in
    if (auth.isLoggedIn()) {
        wsClient.connect();
    }
});

// Chat functionality
function initChatFunctionality() {
    // Toggle between private and group chat in modal
    const chatTypeSelect = document.getElementById('chatType');
    if (chatTypeSelect) {
        const privateUserSelect = document.getElementById('privateUserSelect');
        const groupChatCreate = document.getElementById('groupChatCreate');
        
        chatTypeSelect.addEventListener('change', function() {
            if (this.value === 'private') {
                privateUserSelect.style.display = 'block';
                groupChatCreate.style.display = 'none';
            } else {
                privateUserSelect.style.display = 'none';
                groupChatCreate.style.display = 'block';
            }
        });
    }
    
    // Handle chat selection
    const chatItems = document.querySelectorAll('.chat-item');
    if (chatItems.length) {
        chatItems.forEach(item => {
            item.addEventListener('click', function() {
                // Remove active class from all chat items
                chatItems.forEach(chat => chat.classList.remove('active'));
                // Add active class to clicked chat
                this.classList.add('active');
                
                // In a real app, we'd load the chat messages here
                const chatId = this.getAttribute('data-chat-id');
                console.log(`Selected chat ID: ${chatId}`);
                
                // Update chat header (just a demo)
                const chatName = this.querySelector('h6').textContent;
                const avatarInitials = this.querySelector('.avatar').textContent;
                
                document.querySelector('.chat-header .avatar').textContent = avatarInitials;
                document.querySelector('.chat-header h5').textContent = chatName;
            });
        });
    }
    
    // Handle message form submission
    const messageForm = document.getElementById('messageForm');
    if (messageForm) {
        const messageInput = document.getElementById('messageInput');
        const messagesList = document.getElementById('messagesList');
        
        messageForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const message = messageInput.value.trim();
            if (message) {
                // Get the current chat ID
                const currentChatId = document.querySelector('.chat-item.active')?.getAttribute('data-chat-id');
                if (!currentChatId) {
                    alert('Please select a chat first');
                    return;
                }
                
                // Display the message immediately in the UI
                if (messagesList) {
                    // Clear any placeholder text
                    if (messagesList.querySelector('.text-muted')) {
                        messagesList.innerHTML = '';
                    }
                    
                    // Format current time
                    const now = new Date();
                    const timeString = now.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
                    
                    // Create a message element
                    const messageHtml = `
                    <div class="d-flex justify-content-end mb-2">
                        <div class="card bg-primary text-white" style="max-width: 75%;">
                            <div class="card-body py-2 px-3">
                                <p class="mb-1">${message}</p>
                                <small class="text-white-50">${timeString}</small>
                            </div>
                        </div>
                    </div>
                    `;
                    
                    messagesList.insertAdjacentHTML('beforeend', messageHtml);
                    
                    // Scroll to bottom
                    messagesList.scrollTop = messagesList.scrollHeight;
                    
                    // Also update the chat list item with the new message
                    const chatItem = document.querySelector(`.chat-item[data-chat-id="${currentChatId}"]`);
                    if (chatItem) {
                        // Update last message preview
                        const msgPreview = chatItem.querySelector('p.mb-0');
                        if (msgPreview) {
                            msgPreview.textContent = message;
                        }
                        
                        // Update timestamp
                        const timeElement = chatItem.querySelector('small.text-muted');
                        if (timeElement) {
                            timeElement.textContent = timeString;
                        }
                    }
                }
                
                // Send via WebSocket
                if (wsClient.connected) {
                    wsClient.sendChatMessage(currentChatId, message);
                } else {
                    alert('WebSocket not connected. Please refresh the page and try again.');
                }
                
                // Clear input
                messageInput.value = '';
            }
        });
        
        // Setup typing status
        let typingTimeout;
        messageInput.addEventListener('input', function() {
            const currentChatId = document.querySelector('.chat-item.active')?.getAttribute('data-chat-id');
            if (!currentChatId || !wsClient.connected) return;
            
            // Clear previous timeout
            if (typingTimeout) {
                clearTimeout(typingTimeout);
            }
            
            // Send typing status
            wsClient.sendTypingStatus(currentChatId, true);
            
            // Set timeout to send stopped typing after 3 seconds of inactivity
            typingTimeout = setTimeout(() => {
                wsClient.sendTypingStatus(currentChatId, false);
            }, 3000);
        });
    }
    
    // Setup WebSocket message handlers
    if (wsClient) {
        // Handle incoming chat messages
        wsClient.on('chat', function(data) {
            const currentChatId = document.querySelector('.chat-item.active')?.getAttribute('data-chat-id');
            if (!currentChatId || data.chat_id !== currentChatId) {
                // Message is for a different chat, handle notification here
                // For example, update the unread count or show a notification
                const chatItem = document.querySelector(`.chat-item[data-chat-id="${data.chat_id}"]`);
                if (chatItem) {
                    // Update last message preview
                    const msgPreview = chatItem.querySelector('p.mb-0');
                    if (msgPreview) {
                        msgPreview.textContent = data.content;
                    }
                    
                    // Update timestamp
                    const timestamp = new Date(data.timestamp);
                    if (!isNaN(timestamp)) {
                        const timeString = timestamp.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
                        const timeElement = chatItem.querySelector('small.text-muted');
                        if (timeElement) {
                            timeElement.textContent = timeString;
                        }
                    }
                    
                    // Add unread indicator if not already present
                    if (!chatItem.classList.contains('unread')) {
                        chatItem.classList.add('unread');
                    }
                }
                return;
            }
            
            const messagesList = document.getElementById('messagesList');
            if (!messagesList) return;
            
            // Format timestamp
            const timestamp = new Date(data.timestamp);
            const timeString = timestamp.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
            
            // Check if this is a message we sent
            const isOwnMessage = data.sender_id === currentChatAvatar.getAttribute('data-user-id');
            const isSentConfirmation = isOwnMessage && data.status === 'sent';
            
            // If this is a confirmation of a message we just sent, don't add it again
            // We already added it to the UI when we sent it
            if (isSentConfirmation) {
                return;
            }
            
            // Create a new message element
            const messageHtml = `
            <div class="d-flex justify-content-${isOwnMessage ? 'end' : 'start'} mb-2">
                <div class="card ${isOwnMessage ? 'bg-primary text-white' : 'bg-light'}" style="max-width: 75%;">
                    <div class="card-body py-2 px-3">
                        <p class="mb-1">${data.content}</p>
                        <small class="${isOwnMessage ? 'text-white-50' : 'text-muted'}">${timeString}</small>
                    </div>
                </div>
            </div>
            `;
            
            messagesList.insertAdjacentHTML('beforeend', messageHtml);
            
            // Scroll to bottom
            messagesList.scrollTop = messagesList.scrollHeight;
            
            // Send read receipt if it's not our own message
            if (!isOwnMessage) {
                wsClient.sendReadReceipt(data.message_id);
            }
        });
        
        // Handle typing notifications
        wsClient.on('typing', function(data) {
            const currentChatId = document.querySelector('.chat-item.active')?.getAttribute('data-chat-id');
            if (data.chat_id !== currentChatId) {
                // Typing notification is for a different chat
                return;
            }
            
            const statusElement = document.getElementById('currentChatStatus');
            if (!statusElement) return;
            
            if (data.is_typing) {
                statusElement.textContent = 'typing...';
            } else {
                // Restore original status
                const chatType = document.querySelector('.chat-item.active')?.getAttribute('data-chat-type');
                statusElement.textContent = chatType === 'group' ? 'Group chat' : 'Private chat';
            }
        });
        
        // Handle queued messages
        wsClient.on('queued_messages', function(data) {
            console.log(`Received ${data.count} queued messages`);
            
            // Process each message
            if (data.messages && data.messages.length > 0) {
                data.messages.forEach(message => {
                    // Trigger appropriate handler based on message type
                    wsClient.triggerHandler(message.type, message);
                });
            }
        });
        
        // Handle system messages
        wsClient.on('system', function(data) {
            console.log('System message:', data.message);
        });
        
        // Handle errors
        wsClient.on('error', function(data) {
            console.error('WebSocket error message:', data.message);
        });
    }
} 