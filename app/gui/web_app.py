from nicegui import ui, run, app
import sys
import os
from pathlib import Path

# Ensure project root is in sys.path for direct script execution
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import asyncio
import socket
import webbrowser
import threading
import time
import logging

# 全局变量存储 AppCore 实例
app_core = None

TRANSLATIONS = {
    'en': {
        'kb_management': 'Knowledge Base',
        'ref_count': 'Reference Count (Top-K)',
        'fetching': 'Fetching...',
        'maintenance': 'Maintenance',
        'sync_folder': 'Sync Folder',
        'rebuild_index': 'Rebuild Index',
        'logs': 'Logs',
        'new_chat': 'New Chat',
        'history': 'History',
        'rename': 'Rename',
        'delete': 'Delete',
        'cancel': 'Cancel',
        'save': 'Save',
        'rename_session': 'Rename Session',
        'ask_placeholder': 'Ask anything...',
        'copy': 'Copy',
        'helpful': 'Helpful',
        'not_helpful': 'Not Helpful',
        'loading': 'Loading ExtractHelper...',
        'references': 'References',
        'error': 'Error',
        'language': 'Language',
        'docs': 'Docs',
        'chunks': 'Chunks',
        'kb_stats_error': 'Stats Error',
        'welcome_title': 'ExtractHelper AI',
        'welcome_subtitle': 'Your local knowledge assistant',
    },
    'zh': {
        'kb_management': '资料库管理',
        'ref_count': '引用资料数量 (Top-K)',
        'fetching': '正在获取...',
        'maintenance': '系统维护',
        'sync_folder': '同步目录',
        'rebuild_index': '重建索引',
        'logs': '系统日志',
        'new_chat': '新对话',
        'history': '历史记录',
        'rename': '重命名',
        'delete': '删除',
        'cancel': '取消',
        'save': '保存',
        'rename_session': '重命名会话',
        'ask_placeholder': '询问任何问题...',
        'copy': '复制内容',
        'helpful': '有帮助',
        'not_helpful': '无帮助',
        'loading': '正在加载 ExtractHelper...',
        'references': '参考资料',
        'error': '错误',
        'language': '语言设置',
        'docs': '文档',
        'chunks': '切片',
        'kb_stats_error': '统计错误',
        'welcome_title': 'ExtractHelper AI',
        'welcome_subtitle': '您的本地知识助手',
    }
}

# -----------------------------------------------------------------------------
ui.add_head_html('''
<style>
    :root {
        --primary-color: #6366f1; /* Indigo-500 */
        --bg-color: #f3f4f6; /* Gray-100 */
        --sidebar-bg: #ffffff;
        --chat-user-bg: #e0e7ff; /* Indigo-100 */
        --chat-ai-bg: #ffffff;
    }

    /* Hide NiceGUI default connection/error popups */
    .nicegui-error-popup {
        display: none !important;
    }

    body {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        background-color: var(--bg-color);
        color: #1f2937;
    }

    /* 自定义滚动条 */
    ::-webkit-scrollbar {
        width: 6px;
        height: 6px;
    }
    ::-webkit-scrollbar-track {
        background: transparent; 
    }
    ::-webkit-scrollbar-thumb {
        background: #cbd5e1; 
        border-radius: 3px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #94a3b8; 
    }

    /* 动画 */
    @keyframes fadeInUp {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    .animate-fade-in {
        animation: fadeInUp 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards;
    }
    
    /* 隐藏 NiceGUI 默认的 page padding */
    .nicegui-content {
        padding: 0 !important;
        margin: 0 !important;
        max-width: none !important;
    }

    /* 强制 Left Drawer 背景色，防止底部露白 */
    .q-drawer--left {
        background-color: #f9f9f9 !important;
    }
    
    /* Markdown Styles */
    .markdown-body h1, .markdown-body h2, .markdown-body h3 {
        margin-top: 1.5em;
        margin-bottom: 0.5em;
        font-weight: 600;
        color: #111827;
    }
    .markdown-body p {
        margin-bottom: 1em;
        line-height: 1.7;
    }
    .markdown-body code {
        background-color: #f1f5f9;
        padding: 0.2em 0.4em;
        border-radius: 0.25em;
        font-family: 'Menlo', 'Monaco', 'Courier New', monospace;
        font-size: 0.9em;
        color: #0f172a;
    }
    .markdown-body pre code {
        background-color: transparent;
        padding: 0;
        color: inherit;
    }
    .markdown-body pre {
        background-color: #1e293b;
        color: #f8fafc;
        padding: 1em;
        border-radius: 0.5em;
        overflow-x: auto;
        margin-bottom: 1em;
    }
</style>
''', shared=True)

# -----------------------------------------------------------------------------
# 组件渲染函数
# -----------------------------------------------------------------------------

def render_drawer_content(drawer_container, core_app, app_state):
    """渲染右侧侧边栏 (资料库管理)"""
    t = lambda k: TRANSLATIONS[app_state.get('lang', 'zh')][k]
    drawer_container.clear()
    with drawer_container:
        with ui.row().classes('w-full items-center justify-between mb-6'):
            ui.label(t('kb_management')).classes('text-xl font-bold text-gray-800')
            # 关闭按钮
            ui.button(on_click=lambda: drawer_container.toggle()).props('flat round size=sm color=gray icon=close')

        # Language Switch
        with ui.card().classes('w-full mb-4 bg-white shadow-sm border border-gray-100 p-4 gap-3'):
            ui.label(t('language')).classes('text-xs font-bold text-gray-500 uppercase tracking-wider')
            
            def set_lang(l):
                app_state['lang'] = l
                if 'refresh_ui' in app_state:
                     app_state['refresh_ui']()

            with ui.row().classes('w-full items-center gap-2'):
                 ui.button('English', on_click=lambda: set_lang('en')).props(f'flat={"zh" == app_state.get("lang", "zh")} unelevated={"en" == app_state.get("lang", "zh")} color={"indigo" if "en" == app_state.get("lang", "zh") else "grey"} size=sm').classes('flex-grow')
                 ui.button('中文', on_click=lambda: set_lang('zh')).props(f'flat={"en" == app_state.get("lang", "zh")} unelevated={"zh" == app_state.get("lang", "zh")} color={"indigo" if "zh" == app_state.get("lang", "zh") else "grey"} size=sm').classes('flex-grow')

        # 1. 检索设置
        with ui.card().classes('w-full mb-4 bg-white shadow-sm border border-gray-100 p-4 gap-3'):
            ui.label(t('ref_count')).classes('text-xs font-bold text-gray-500 uppercase tracking-wider')
            with ui.row().classes('w-full items-center gap-4'):
                ui.slider(min=1, max=20, step=1).bind_value(app_state, 'top_k').classes('flex-grow')
                ui.label().bind_text_from(app_state, 'top_k').classes('font-mono font-bold w-6 text-right text-xs text-indigo-500')

        # 2. 系统状态
        with ui.card().classes('w-full mb-4 bg-white shadow-sm border border-gray-100 p-4'):
            status_label = ui.label(t('fetching')).classes('text-xs font-mono text-gray-600 break-all')
        
        def refresh_stats():
            try:
                stats = core_app.kb.get_stats()
                status_label.set_text(f"{t('docs')}: {stats['documents']} | {t('chunks')}: {stats['chunks']}")
            except Exception as e:
                status_label.set_text(f"{t('kb_stats_error')}: {e}")
        
        refresh_stats()

        # 3. 操作按钮
        ui.label(t('maintenance')).classes('text-xs font-bold text-gray-400 mb-2 uppercase tracking-wider')
        with ui.column().classes('w-full gap-2'):
            async def run_kb_task(task_type):
                log.push(f"[{task_type}] ...")
                try:
                    if task_type == 'sync':
                        await run.io_bound(core_app.kb.sync_folder)
                    elif task_type == 'rebuild':
                        await run.io_bound(core_app.kb.rebuild_index)
                    elif task_type == 'compact':
                        await run.io_bound(core_app.kb.compact)
                    log.push(f"[{task_type}] Done")
                    refresh_stats()
                except Exception as e:
                    log.push(f"Error: {e}")

            with ui.button(on_click=lambda: run_kb_task('sync')).classes('w-full').props('outline size=sm color=teal'):
                ui.icon('sync', size='xs').classes('mr-2')
                ui.label(t('sync_folder'))
            
            with ui.button(on_click=lambda: run_kb_task('rebuild')).classes('w-full').props('outline size=sm color=orange'):
                ui.icon('build', size='xs').classes('mr-2')
                ui.label(t('rebuild_index'))

        # 4. 日志
        ui.separator().classes('my-4')
        ui.label(t('logs')).classes('text-xs font-bold text-gray-400 mb-2 uppercase tracking-wider')
        log = ui.log(max_lines=200).classes('w-full h-32 text-[10px] bg-gray-900 text-green-400 p-2 rounded font-mono shadow-inner leading-tight')
        
        # 简单劫持 stdout
        class LogElementWriter:
            def write(self, text):
                if text.strip(): log.push(text.strip())
            def flush(self): pass
        sys.stdout = LogElementWriter()


def render_left_drawer(drawer, core_app, app_state, load_session_callback):
    """渲染左侧会话列表"""
    t = lambda k: TRANSLATIONS[app_state.get('lang', 'zh')][k]
    drawer.clear()
    with drawer:
        # 1. New Chat Button (Prominent)
        with ui.button(on_click=lambda: load_session_callback(None)).classes('mx-3 mt-4 mb-6 rounded-xl shadow-sm border border-gray-200 hover:shadow-md transition-all duration-300').props('unelevated color=white text-color=grey-9'):
            with ui.row().classes('items-center gap-3 w-full py-2 justify-center'):
                ui.icon('add', size='xs').classes('text-indigo-500')
                ui.label(t('new_chat')).classes('text-sm font-bold tracking-wide text-gray-700')
        
        # 2. Session List
        ui.label(t('history')).classes('text-xs font-bold text-gray-400 mb-3 px-4 uppercase tracking-wider')
        
        sessions = core_app.chat_manager.list_sessions()
        
        with ui.scroll_area().classes('w-full flex-grow px-3'): 
            with ui.column().classes('w-full gap-1'):
                for s in sessions:
                    sid = s['id']
                    title = s['title'] or "未命名会话"
                    is_active = app_state.get('current_session_id') == sid
                    
                    # Style: Clean, simple rows with subtle hover
                    row_classes = 'w-full items-center justify-between rounded-lg group transition-all duration-200 cursor-pointer h-10 px-3 '
                    if is_active:
                        row_classes += 'bg-indigo-50 text-indigo-900 font-medium'
                    else:
                        row_classes += 'hover:bg-gray-50 text-gray-700'
                    
                    with ui.row().classes(row_classes):
                        # Title with icon
                        with ui.row().classes('items-center gap-3 flex-grow overflow-hidden'):
                            ui.icon('chat_bubble_outline', size='xs').classes('text-gray-400')
                            ui.label(title).classes('text-sm truncate flex-grow').on('click', lambda i=sid: load_session_callback(i))
                        
                        # Actions Logic
                        async def delete_handler(i=sid):
                            core_app.chat_manager.delete_session(i)
                            if app_state.get('current_session_id') == i:
                                load_session_callback(None)
                            else:
                                render_left_drawer(drawer, core_app, app_state, load_session_callback)

                        def rename_session(i, new_title):
                            if new_title and new_title.strip():
                                core_app.chat_manager.update_title(i, new_title.strip())
                                render_left_drawer(drawer, core_app, app_state, load_session_callback)

                        def open_rename_dialog(i, current_title):
                            with ui.dialog() as dialog, ui.card().classes('min-w-[320px] p-6 rounded-2xl shadow-xl'):
                                ui.label(t('rename_session')).classes('text-lg font-bold mb-4 text-gray-800')
                                name_input = ui.input(value=current_title).classes('w-full mb-6').props('autofocus outlined rounded dense')
                                with ui.row().classes('w-full justify-end gap-3'):
                                    ui.button(t('cancel'), on_click=dialog.close).props('flat color=grey rounded')
                                    ui.button(t('save'), on_click=lambda: [rename_session(i, name_input.value), dialog.close()]).props('unelevated color=indigo rounded')
                            dialog.on('close', dialog.delete)
                            dialog.open()

                        # More Options Menu
                        btn_color = 'text-indigo-400' if is_active else 'text-gray-400'
                        with ui.button(icon='more_vert').props('flat round size=xs').classes(f'opacity-0 group-hover:opacity-100 transition-opacity {btn_color}'):
                            with ui.menu().classes('shadow-xl border border-gray-100 rounded-xl p-1 min-w-[140px] bg-white'):
                                with ui.menu_item(on_click=lambda i=sid, t=title: open_rename_dialog(i, t)).classes('rounded-lg hover:bg-gray-50 transition-colors'):
                                    with ui.row().classes('items-center gap-3 w-full px-2 py-1'):
                                        ui.icon('edit', size='xs').classes('text-gray-500')
                                        ui.label(t('rename')).classes('text-sm text-gray-700 font-medium')
                                
                                with ui.menu_item(on_click=lambda i=sid: delete_handler(i)).classes('rounded-lg hover:bg-red-50 transition-colors'):
                                    with ui.row().classes('items-center gap-3 w-full px-2 py-1'):
                                        ui.icon('delete', size='xs').classes('text-red-500')
                                        ui.label(t('delete')).classes('text-sm text-red-500 font-medium')


def render_chat_messages(container, history, app_state=None):
    """渲染历史消息列表"""
    lang = app_state.get('lang', 'zh') if app_state else 'zh'
    t = lambda k: TRANSLATIONS[lang][k]
    
    container.clear()
    with container:
        if not history:
             # 空状态 - 居中 Logo
             with ui.column().classes('w-full items-center justify-center mt-24 opacity-0 animate-fade-in'):
                # 现代风格的 Logo / 欢迎页
                with ui.card().classes('w-24 h-24 rounded-3xl bg-indigo-500 items-center justify-center shadow-lg mb-6 flex'):
                    ui.icon('auto_awesome', size='3rem', color='white')
                ui.label(t('welcome_title')).classes('text-3xl font-bold text-gray-800 tracking-tight')
                ui.label(t('welcome_subtitle')).classes('text-gray-400 font-medium text-sm mt-2')
             return

        # 消息流
        for msg in history:
            role = msg['role']
            content = msg['content']
            evidence = msg.get('evidence')
            
            # Message Container
            with ui.row().classes('w-full mb-6 animate-fade-in group items-start'):
                if role == 'user':
                    # User: Right side
                    with ui.row().classes('w-full justify-end gap-4'):
                        with ui.column().classes('items-end max-w-[85%]'):
                            with ui.card().classes('bg-[#e0e7ff] px-5 py-3.5 rounded-2xl rounded-tr-sm shadow-sm border border-indigo-100/50'):
                                ui.label(content).classes('text-gray-800 text-base leading-relaxed whitespace-pre-wrap')
                        ui.avatar(icon='person', color='indigo-100', text_color='indigo-600').classes('mt-1 shadow-sm ring-2 ring-indigo-50')
                else:
                    # AI: Left side
                    with ui.row().classes('w-full justify-start gap-4 px-2'):
                        ui.avatar(icon='auto_awesome', color='indigo-600', text_color='white').classes('mt-1 shadow-md ring-2 ring-indigo-50')
                        
                        with ui.column().classes('flex-grow min-w-0 max-w-4xl gap-1'):
                            # AI Name
                            ui.label('ExtractHelper').classes('font-bold text-sm text-gray-900 ml-1')
                            
                            # Content Bubble (Transparent for AI, Markdown)
                            # 使用 markdown-body 类应用自定义样式
                            ui.markdown(content).classes('markdown-body text-gray-800 text-base leading-relaxed w-full overflow-hidden')
                            
                            # Evidence Section (Styled)
                            if evidence:
                                 with ui.expansion(f'{t("references")} ({len(evidence)})', icon='menu_book').classes('w-full bg-white border border-gray-200 rounded-xl text-xs text-gray-500 mt-3 shadow-sm hover:shadow-md transition-shadow duration-300'):
                                        with ui.column().classes('gap-3 p-3 bg-gray-50'):
                                            for i, e in enumerate(evidence, 1):
                                                with ui.link(target='#').classes('no-underline group/link w-full bg-white p-2 rounded-lg border border-gray-100 hover:border-indigo-300 transition-colors'):
                                                    with ui.row().classes('items-center gap-2 mb-1'):
                                                        ui.label(f"#{i}").classes('font-mono font-bold text-xs text-indigo-500 bg-indigo-50 px-1.5 rounded')
                                                        ui.label(e['filename']).classes('font-bold text-xs text-gray-700 truncate flex-grow')
                                                        ui.label(f"Score: {e['score']:.2f}").classes('text-[10px] text-gray-400')
                                                    ui.label(e.get('snippet', '').strip()[:120] + '...').classes('text-[11px] text-gray-500 leading-relaxed font-mono pl-1')

                            # Action Bar
                            with ui.row().classes('gap-1 mt-2 ml-1 opacity-0 group-hover:opacity-100 transition-opacity duration-200'):
                                with ui.button(icon='content_copy', on_click=lambda c=content: ui.clipboard.write(c)).props('flat round size=xs color=grey'):
                                    ui.tooltip(t('copy'))
                                with ui.button(icon='thumb_up_off_alt').props('flat round size=xs color=grey'):
                                    ui.tooltip(t('helpful'))
                                with ui.button(icon='thumb_down_off_alt').props('flat round size=xs color=grey'):
                                    ui.tooltip(t('not_helpful'))


# -----------------------------------------------------------------------------
# 页面入口
# -----------------------------------------------------------------------------

@ui.page('/')
async def main_page():
    global app_core
    
    # 客户端状态
    app_state = {
        'current_session_id': None,
        'history': [],
        'top_k': 5,
        'kb_enabled': True,
        'lang': 'zh'
    }
    
    t = lambda k: TRANSLATIONS[app_state['lang']][k]

    # --- UI 结构 (使用 Drawer + Main Layout) ---
    
    # 1. Left Drawer (Chat List)
    # bg-[#f9f9f9] 模仿 ChatGPT 侧边栏颜色
    # fixed 属性确保其占据全高，z-index 确保层级
    left_drawer = ui.left_drawer(value=True).classes('bg-[#f9f9f9] border-r border-gray-200 w-[260px] p-0 flex flex-col h-full').props('elevated=False bordered')

    # 2. Right Drawer (Settings)
    # 增加 overlay 属性以便点击遮罩关闭，或者保持 fixed 但提供关闭按钮
    right_drawer = ui.right_drawer(value=False).classes('bg-white border-l border-gray-200 p-6 w-[320px]')

    # 3. Main Content
    # 使用 header 替代自定义 row 以保证布局正确
    with ui.header(elevated=False).classes('bg-white/90 backdrop-blur-sm border-b border-gray-200 h-[60px] flex items-center px-4 text-gray-800'):
        # Left: Toggle Sidebar
        with ui.button(on_click=lambda: left_drawer.toggle()).props('flat round color=gray icon=menu size=md').classes('xl:hidden mr-2'):
            pass
        
        # Center: Title
        with ui.row().classes('items-center gap-2 cursor-pointer hover:bg-gray-100 px-3 py-1 rounded-lg transition-colors mx-auto'):
             ui.icon('auto_awesome', size='xs').classes('text-indigo-500')
             ui.label('ExtractHelper').classes('text-lg font-bold text-gray-700 tracking-tight')
             ui.badge('1.0', color='indigo-100', text_color='indigo-500').props('rounded').classes('text-[10px] font-bold px-1.5')
        
        # Right: Settings
        with ui.row().classes('items-center gap-1'):
             with ui.button(on_click=lambda: right_drawer.toggle()).props('flat round color=gray icon=settings size=sm'):
                pass

    # Main Column - NiceGUI 会自动处理 header/footer/drawer 的偏移
    with ui.column().classes('w-full p-0 m-0 relative items-center flex-grow'):
        
        # B. Chat Scroll Area
        # 调整高度计算以适应新的 Header (60px) 和 Footer 留白
        chat_scroll = ui.scroll_area().classes('w-full h-[calc(100vh-140px)] px-4 md:px-0')
        
        with chat_scroll:
            chat_container = ui.column().classes('w-full max-w-3xl mx-auto py-6 gap-0')
            
            # 初始渲染 Loading 或 欢迎页
            # (将在 init_task 中填充)

    # C. Input Area in Footer
    # 使用 footer 保证始终在底部，且宽度自适应
    with ui.footer().classes('bg-transparent p-0 mb-6 border-none pointer-events-none'):
        # 实际输入框容器 (pointer-events-auto)
        with ui.column().classes('w-full max-w-3xl mx-auto px-4 pointer-events-auto'):
             with ui.row().classes('w-full bg-white/80 backdrop-blur-md rounded-[26px] px-4 py-3 items-end gap-3 shadow-lg border border-gray-200 focus-within:border-indigo-300 focus-within:ring-4 focus-within:ring-indigo-50/50 transition-all duration-300'):
                
                # Text Input
                text_input = ui.textarea(placeholder=t('ask_placeholder')).props('borderless autogrow rows=1 max-rows=8').classes('flex-grow text-base bg-transparent p-0 my-0.5 max-h-[200px] overflow-y-auto placeholder-gray-400')
                
                # Send Button logic
                async def send():
                    text = text_input.value.strip()
                    if not text: return
                    text_input.value = ''
                    
                    # 1. User Msg
                    app_state['history'].append({'role': 'user', 'content': text})
                    render_chat_messages(chat_container, app_state['history'], app_state)
                    chat_scroll.scroll_to(percent=1.0, duration=0.2)
                    
                    # 2. Session Logic
                    if app_state['current_session_id'] is None:
                        title = text[:20] + "..." if len(text) > 20 else text
                        sid = app_core.chat_manager.create_new_session(title)
                        app_state['current_session_id'] = sid
                        app_core.chat_manager.add_user_message(sid, text)
                        render_left_drawer(left_drawer, app_core, app_state, load_session)
                    else:
                        app_core.chat_manager.add_user_message(app_state['current_session_id'], text)
                    
                    # 3. Loading
                    spinner_id = f'spinner_{int(time.time())}'
                    with chat_container:
                        with ui.row().classes('w-full items-start gap-4 animate-fade-in').id(spinner_id):
                             ui.avatar(icon='smart_toy', color='white', text_color='teal-600').classes('size-8 border border-gray-200 mt-1')
                             ui.spinner(size='1.5rem', color='teal').classes('mt-2')
                    chat_scroll.scroll_to(percent=1.0, duration=0.2)
                    
                    # 4. RAG Task
                    try:
                        k = app_state['top_k']
                        context_history = app_state['history'][:-1]
                        ans, ev, _ = await run.io_bound(app_core.rag.ask, text, history=context_history, top_k=k)
                        
                        # Save & Update
                        app_core.chat_manager.add_ai_message(app_state['current_session_id'], ans, ev)
                        app_state['history'].append({'role': 'assistant', 'content': ans, 'evidence': ev})
                    except Exception as e:
                        app_state['history'].append({'role': 'assistant', 'content': f"Error: {str(e)}"})
                    
                    # Remove spinner & Render
                    # (Simple way: re-render all. Optimized way: remove spinner element and append msg. Here we re-render for simplicity)
                    render_chat_messages(chat_container, app_state['history'], app_state)
                    chat_scroll.scroll_to(percent=1.0, duration=0.2)

                # Bind Enter key (Need JS for Textarea Enter-to-submit without Shift)
                text_input.on('keydown.enter.prevent', lambda e: send() if not e.args['shiftKey'] else None)

                # Right Icons
                with ui.row().classes('items-center gap-1 mb-1'):
                     # Send Button
                     with ui.button(on_click=send).props('flat round icon=arrow_upward size=sm').classes('bg-gray-800 text-white hover:bg-black transition-colors'):
                        pass



    # --- Logic & Init ---

    def load_session(session_id):
        """加载会话"""
        if app_core is None: return
        
        app_state['current_session_id'] = session_id
        if session_id:
            app_state['history'] = app_core.chat_manager.get_history(session_id)
        else:
            app_state['history'] = []
            
        render_chat_messages(chat_container, app_state['history'], app_state)
        render_left_drawer(left_drawer, app_core, app_state, load_session)
        
        # 移动端自动关闭侧边栏
        # if ui.context.client.layout.width < 1024: left_drawer.hide()

    def refresh_ui():
        # Update placeholder
        text_input.props(f'placeholder="{t("ask_placeholder")}"')
        
        render_drawer_content(right_drawer, app_core, app_state)
        render_left_drawer(left_drawer, app_core, app_state, load_session)
        render_chat_messages(chat_container, app_state['history'], app_state)
    
    app_state['refresh_ui'] = refresh_ui

    def _create_app_instance():
        """
        在子线程中执行初始化，避免 import 导致的长时间阻塞。
        """
        print("Initializing AppCore in background thread...")
        from app.app_core import ExtractHelperApp
        return ExtractHelperApp()

    async def init_task():
        global app_core
        if app_core is None:
            try:
                # 在线程池中执行实例化（包括 import 耗时操作）
                app_core = await run.io_bound(_create_app_instance)
                print("AppCore initialized successfully.")
                
                # Init UI
                refresh_ui()
                
            except Exception as e:
                print(f"Initialization failed: {e}")
                ui.notify(f"Initialization failed: {e}", type='negative')
        else:
             refresh_ui()

    # Startup Loading
    if app_core is None:
        with chat_container:
            with ui.column().classes('w-full items-center justify-center pt-20 gap-4'):
                ui.spinner(size='3rem', color='teal')
                ui.label(t('loading')).classes('text-gray-500 animate-pulse')
        ui.timer(0.1, init_task, once=True)
    else:
        refresh_ui()


# -----------------------------------------------------------------------------
# Main Execution
# -----------------------------------------------------------------------------

def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]

if __name__ in {"__main__", "__mp_main__"}:
    port = find_free_port()
    print(f"Starting ExtractHelper on port {port}...")
    
    def open_browser():
        time.sleep(1.5)
        # webbrowser.open(f'http://localhost:{port}')
    
    threading.Thread(target=open_browser, daemon=True).start()
    ui.run(title='ExtractHelper', port=port, reload=False, native=False, favicon='🤖')
