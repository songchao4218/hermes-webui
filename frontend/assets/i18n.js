// 马鞍 Ma'an - Internationalization
// 支持英文和中文

const i18n = {
  en: {
    // Onboarding
    onboard: {
      welcome: 'Welcome to 马鞍 Ma\'an',
      namePlaceholder: 'e.g. Atlas, Hoshino, Miku 🎵',
      subtitlePlaceholder: 'Local Intelligence',
      avatar: 'Choose an Avatar',
      avatarHint: 'Upload an image for your agent, or use the default.',
      avatarFormats: 'PNG, JPG, GIF, WEBP',
      skipAvatar: 'Skip — use default',
      theme: 'Pick a Theme',
      themeHint: 'Choose an accent color for your interface.',
      customColor: 'Custom:',
      preview: 'Your Agent',
      done: 'Get Started',
      local: 'Everything is stored locally on your machine.',
      changeLater: 'You can change this anytime in Settings.'
    },
    // Navigation
    nav: {
      chat: 'Chat',
      skills: 'Skills',
      memory: 'Memory',
      settings: 'Settings',
      newChat: 'New Chat'
    },
    // Chat
    chat: {
      empty: 'Start a conversation',
      sync: 'Memory synced with Hermes CLI',
      thinking: 'is thinking...',
      latency: 'Latency',
      model: 'Model',
      memory: 'Memory',
      placeholder: 'Type a message...'
    },
    // Skills
    skills: {
      title: 'Installed Skills',
      none: 'No skills installed',
      empty: 'No skills installed',
      error: 'Failed to load skills'
    },
    // Memory
    memory: {
      title: 'Memory System',
      hint: 'These memory files are shared with Hermes CLI. Changes apply to both.',
      soul: 'SOUL.md',
      soulDesc: "Agent's core personality, name, behavior rules",
      memory: 'MEMORY.md',
      memoryDesc: "Agent's accumulated knowledge and context",
      user: 'USER.md',
      userDesc: 'User profile information',
      edit: 'Edit',
      save: 'Save',
      saved: 'Memory saved!'
    },
    // Settings
    settings: {
      title: 'Settings',
      identity: 'Agent Identity',
      avatar: 'Avatar',
      name: 'Agent Name',
      namePlaceholder: 'Give your agent a name...',
      subtitle: 'Subtitle',
      subtitlePlaceholder: 'Local Intelligence',
      theme: 'Theme Color',
      customColor: 'Custom color:',
      system: 'System Info',
      save: 'Save Changes',
      saved: 'Settings saved!'
    },
    // Status
    status: {
      connecting: 'Connecting...',
      online: 'Online',
      offline: 'Offline',
      hermesHome: 'Hermes Home',
      ollamaUrl: 'Ollama URL',
      defaultModel: 'Default Model',
      connection: 'Connection',
      connected: 'Connected',
      disconnected: 'Disconnected'
    },
    // Skills
    skill: {
      use: 'Use skill'
    },
    // Error
    error: {
      noResponse: 'No response received.',
      saveFailed: 'Save failed:',
      ollamaUnreachable: 'Ollama unreachable',
      requestFailed: 'Request failed:'
    }
  },
  zh: {
    // Onboarding
    onboard: {
      welcome: '欢迎使用 马鞍 Ma\'an',
      namePlaceholder: '例如：阿特拉斯、星野、初音 🎵',
      subtitlePlaceholder: '本地智能',
      avatar: '选择头像',
      avatarHint: '为您的代理上传图片，或使用默认头像。',
      avatarFormats: 'PNG、JPG、GIF、WEBP',
      skipAvatar: '跳过 — 使用默认',
      theme: '选择主题',
      themeHint: '为您的界面选择强调色。',
      customColor: '自定义：',
      preview: '您的代理',
      done: '开始使用',
      local: '所有内容都存储在您的本地机器上。',
      changeLater: '您可以随时在设置中更改这些设置。'
    },
    // Navigation
    nav: {
      chat: '聊天',
      skills: '技能',
      memory: '记忆',
      settings: '设置',
      newChat: '新聊天'
    },
    // Chat
    chat: {
      empty: '开始对话',
      sync: '记忆与 Hermes CLI 同步',
      thinking: '正在思考...',
      latency: '延迟',
      model: '模型',
      memory: '记忆',
      placeholder: '输入消息...'
    },
    // Skills
    skills: {
      title: '已安装技能',
      none: '未安装技能',
      empty: '未安装技能',
      error: '加载技能失败'
    },
    // Memory
    memory: {
      title: '记忆系统',
      hint: '这些记忆文件与 Hermes CLI 共享。更改会同时应用到两者。',
      soul: 'SOUL.md',
      soulDesc: '代理的核心个性、名称、行为规则',
      memory: 'MEMORY.md',
      memoryDesc: '代理积累的知识和上下文',
      user: 'USER.md',
      userDesc: '用户个人资料信息',
      edit: '编辑',
      save: '保存',
      saved: '记忆已保存！'
    },
    // Settings
    settings: {
      title: '设置',
      identity: '代理身份',
      avatar: '头像',
      name: '代理名称',
      namePlaceholder: '给您的代理起个名字...',
      subtitle: '副标题',
      subtitlePlaceholder: '本地智能',
      theme: '主题颜色',
      customColor: '自定义颜色：',
      system: '系统信息',
      save: '保存更改',
      saved: '设置已保存！'
    },
    // Status
    status: {
      connecting: '连接中...',
      online: '在线',
      offline: '离线',
      hermesHome: 'Hermes 主目录',
      ollamaUrl: 'Ollama URL',
      defaultModel: '默认模型',
      connection: '连接状态',
      connected: '已连接',
      disconnected: '未连接'
    },
    // Skills
    skill: {
      use: '使用技能'
    },
    // Error
    error: {
      noResponse: '未收到响应。',
      saveFailed: '保存失败：',
      ollamaUnreachable: 'Ollama 不可达',
      requestFailed: '请求失败：'
    }
  }
};

// 检测浏览器语言
function detectLanguage() {
  const lang = navigator.language || navigator.userLanguage;
  return lang.startsWith('zh') ? 'zh' : 'en';
}

// 保存语言设置
function saveLanguage(lang) {
  localStorage.setItem('maan_language', lang);
}

// 加载语言设置
function loadLanguage() {
  return localStorage.getItem('maan_language') || detectLanguage();
}

// 切换语言
function switchLanguage(lang) {
  saveLanguage(lang);
  updateUI(lang);
}

// 获取当前语言的文本
function t(key) {
  const lang = loadLanguage();
  const keys = key.split('.');
  let value = i18n[lang];
  for (const k of keys) {
    value = value?.[k];
  }
  return value || key;
}

// 更新UI
function updateUI(lang) {
  // 这里会在前端代码中实现
}

export { i18n, t, switchLanguage, loadLanguage, detectLanguage };