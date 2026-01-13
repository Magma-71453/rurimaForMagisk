let currentContainer = null;

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    loadContainers();
    setupTabs();
});

// 设置底部 Tab 逻辑
function setupTabs() {
    const tabs = document.querySelectorAll('.bottom-tab a');
    tabs.forEach(tab => {
        tab.addEventListener('click', (e) => {
            e.preventDefault(); // 防止 href="#" 跳转页面顶部
            
            // 移除所有 active
            tabs.forEach(t => t.classList.remove('active'));
            // 激活当前
            e.target.classList.add('active');
            
            const action = e.target.getAttribute('data-action');
            if (action === 'home') {
                document.getElementById('container-list').style.display = 'block';
                loadContainers();
            } else if (action === 'settings') {
                alert("设置功能开发中\nSettings are under construction.");
            }
        });
    });
}

function loadContainers() {
    const list = document.getElementById('container-list');
    
    fetch('api/list.cgi')
        .then(res => {
            // 如果 HTTP 状态码不是 200 (例如 500 脚本错误)
            if (!res.ok) {
                return res.text().then(text => { throw new Error(`HTTP ${res.status}: ${text}`) });
            }
            return res.json();
        })
        .then(data => {
            list.innerHTML = '';
            if (!Array.isArray(data) || data.length === 0) {
                list.innerHTML = '<div style="text-align:center;color:#666;margin-top:20px;">No containers found.<br>Try adding one manually.</div>';
                return;
            }
            data.forEach(c => {
                const card = document.createElement('div');
                card.className = `card ${c.status}`; // running or stopped
                card.innerHTML = `
                    <div class="card-info" onclick="openConfig('${c.name}', '${c.path}', '${c.autostart}')">
                        <h3>${c.name} ${c.autostart === 'true' ? '<span style="color:var(--accent);font-size:0.8em">⚡</span>' : ''}</h3>
                        <p>${c.type.toUpperCase()} | ${c.path}</p>
                    </div>
                    <div class="card-actions">
                        <label class="switch">
                            <input type="checkbox" ${c.status === 'running' ? 'checked' : ''} 
                                onchange="toggleContainer(this, '${c.name}', '${c.path}')">
                            <span class="slider"></span>
                        </label>
                    </div>
                `;
                list.appendChild(card);
            });
        })
        .catch(err => {
            console.error(err);
            list.innerHTML = `<div style="color:#ff5555;text-align:center;padding:20px;">
                <strong>API Error</strong><br>
                <small>${err.message}</small><br><br>
                <small>Check 'chmod +x' on *.cgi<br>Check line endings (LF only)</small>
            </div>`;
        });
}

function toggleContainer(el, name, path) {
    const action = el.checked ? 'start' : 'stop';
    el.disabled = true;
    
    // UI 立即反馈 (Loading 状态)
    el.parentNode.querySelector('.slider').style.backgroundColor = '#555';

    fetch('api/manage.cgi', {
        method: 'POST',
        body: JSON.stringify({ action, name, path })
    })
    .then(res => res.json())
    .then(data => {
        // 成功后刷新列表
        setTimeout(() => {
            el.disabled = false;
            loadContainers();
        }, 1000);
    })
    .catch(err => {
        alert("Control Failed: " + err.message);
        el.disabled = false;
        // 回滚开关状态
        el.checked = !el.checked;
    });
}

// === 模态框逻辑 ===
function closeModal(id) {
    document.getElementById(id).classList.add('hidden');
}

function openConfig(name, path, autostart) {
    currentContainer = { name, path };
    document.getElementById('modal-title').innerText = name;
    // 确保 autostart 转换为布尔值
    document.getElementById('modal-autostart').checked = (String(autostart) === 'true');
    
    const kvList = document.getElementById('kv-list');
    kvList.innerHTML = '<div style="text-align:center;padding:10px;">Loading...</div>';
    document.getElementById('config-modal').classList.remove('hidden');

    fetch('api/manage.cgi', {
        method: 'POST',
        body: JSON.stringify({ action: 'get_config', name: name })
    })
    .then(res => res.json())
    .then(config => {
        kvList.innerHTML = '';
        if (Array.isArray(config) && config.length > 0) {
            config.forEach(item => {
                if(item.key && item.key !== "AUTOSTART") addRow(item.key, item.value);
            });
        }
        // 补齐空白行
        const needed = 3 - (Array.isArray(config) ? config.length : 0);
        for(let i=0; i<Math.max(1, needed); i++) addRow('', '');
    })
    .catch(() => {
        kvList.innerHTML = '<div style="color:red">Failed to load config</div>';
    });
}

function addRow(key, val) {
    const div = document.createElement('div');
    div.className = 'kv-row';
    div.innerHTML = `
        <input type="text" placeholder="-m" value="${key || ''}">
        <input type="text" placeholder="/sdcard" value="${val || ''}">
    `;
    document.getElementById('kv-list').appendChild(div);
}

function addConfigRow() { addRow('', ''); }

function saveConfig() {
    const rows = document.querySelectorAll('.kv-row');
    const configData = [];
    rows.forEach(row => {
        const inputs = row.querySelectorAll('input');
        const k = inputs[0].value.trim();
        const v = inputs[1].value.trim();
        if(k) configData.push({ key: k, value: v });
    });
    
    const isAuto = document.getElementById('modal-autostart').checked;

    fetch('api/manage.cgi', {
        method: 'POST',
        body: JSON.stringify({
            action: 'save',
            name: currentContainer.name,
            autostart: isAuto,
            config: configData
        })
    }).then(() => {
        closeModal('config-modal');
        loadContainers();
    });
}

// === 手动添加 ===
function openAddModal() {
    document.getElementById('add-name').value = '';
    document.getElementById('add-path').value = '';
    document.getElementById('add-modal').classList.remove('hidden');
}

function submitAdd() {
    const name = document.getElementById('add-name').value.trim();
    const path = document.getElementById('add-path').value.trim();
    const type = document.getElementById('add-type').value;

    if (!name || !path) { alert("Please fill info"); return; }

    fetch('api/manage.cgi', {
        method: 'POST',
        body: JSON.stringify({ action: 'add_manual', name, path, type })
    })
    .then(res => res.json())
    .then(data => {
        if(data.status === 'success') {
            closeModal('add-modal');
            loadContainers();
        } else {
            alert(data.message);
        }
    });
}
