import gradio as gr
from database import db
from config import config
from datetime import datetime, timedelta

class WebAdminPanel:
    def __init__(self):
        self.secret = config.ADMIN_SECRET
    
    def verify(self, password):
        return password == self.secret
    
    def get_stats_dashboard(self):
        stats = db.get_stats(7)
        return f"""
        ## 📊 Последние 7 дней
        
        | Метрика | Значение |
        |---------|----------|
        | Новых пользователей | {stats['new_users']} |
        | Всего сообщений | {stats['total_messages']} |
        | Всего пользователей | {stats['total_users']} |
        | Premium пользователей | {stats['premium_users']} |
        | Рефералов | {stats['referrals_total']} |
        | Конверсия рефералов | {stats['conversion_rate']} |
        """
    
    def search_user(self, user_id):
        user = db.get_user(int(user_id))
        if not user:
            return "Пользователь не найден"
        
        premium_status = "Активен" if db.is_premium(user['user_id']) else "Нет"
        
        return f"""
        ## 👤 Пользователь {user['user_id']}
        
        - Username: @{user['username'] or 'Нет'}
        - Язык: {user['language']}
        - Premium: {premium_status} (до {user['premium_until'] or 'Н/Д'})
        - Всего сообщений: {user['total_messages']}
        - Рефералов: {user['referral_count']}
        - Бонусных сообщений: {user['bonus_messages']}
        - Последняя активность: {user['last_active'][:10] if user['last_active'] else 'Н/Д'}
        """
    
    def give_premium(self, user_id, days, password):
        if not self.verify(password):
            return "❌ Неверный пароль"
        
        try:
            db.add_premium(int(user_id), int(days))
            return f"✅ Premium выдан пользователю {user_id} на {days} дней"
        except Exception as e:
            return f"❌ Ошибка: {e}"
    
    def add_messages(self, user_id, count, password):
        if not self.verify(password):
            return "❌ Неверный пароль"
        
        try:
            db.add_bonus_messages(int(user_id), int(count))
            return f"✅ Добавлено {count} сообщений пользователю {user_id}"
        except Exception as e:
            return f"❌ Ошибка: {e}"
    
    def get_inactive_list(self, days):
        users = db.get_inactive_users(int(days))
        if not users:
            return f"Нет неактивных пользователей (>{days} дней)"
        
        result = f"## 😴 Неактивные (> {days} дней)\n\n"
        for uid, username, lang, last in users[:20]:  # Первые 20
            result += f"- @{username or uid} ({lang}), последняя активность: {last[:10]}\n"
        
        return result
    
    def launch(self):
        with gr.Blocks(title="Night Whisper Admin", theme=gr.themes.Soft()) as demo:
            gr.Markdown("🌙 **Night Whisper — Панель управления**")
            
            with gr.Tab("📊 Статистика"):
                gr.Button("Обновить").click(self.get_stats_dashboard, outputs=gr.Markdown())
                stats_output = gr.Markdown(value=self.get_stats_dashboard())
            
            with gr.Tab("👤 Пользователь"):
                user_id = gr.Number(label="User ID")
                search_btn = gr.Button("Найти")
                user_info = gr.Markdown()
                search_btn.click(self.search_user, inputs=user_id, outputs=user_info)
                
                with gr.Row():
                    prem_days = gr.Number(label="Дней Premium", value=30)
                    msg_count = gr.Number(label="Бонус сообщений", value=10)
                    admin_pass = gr.Textbox(label="Пароль админа", type="password")
                
                with gr.Row():
                    give_prem_btn = gr.Button("Выдать Premium")
                    add_msg_btn = gr.Button("Добавить сообщения")
                
                action_result = gr.Markdown()
                give_prem_btn.click(self.give_premium, 
                    inputs=[user_id, prem_days, admin_pass], 
                    outputs=action_result)
                add_msg_btn.click(self.add_messages,
                    inputs=[user_id, msg_count, admin_pass],
                    outputs=action_result)
            
            with gr.Tab("😴 Неактивные"):
                inactive_days = gr.Dropdown([1, 3, 7, 14, 30], label="Дней неактивности", value=7)
                show_btn = gr.Button("Показать")
                inactive_list = gr.Markdown()
                show_btn.click(self.get_inactive_list, inputs=inactive_days, outputs=inactive_list)
            
            with gr.Tab("📢 Рассылка"):
                gr.Markdown("Массовая рассылка")
                broadcast_text = gr.Textbox(label="Текст сообщения", lines=5)
                broadcast_pass = gr.Textbox(label="Пароль", type="password")
                broadcast_btn = gr.Button("Отправить всем")
                broadcast_result = gr.Markdown()
                # Здесь логика рассылки
        
        demo.launch(server_name="0.0.0.0", server_port=config.WEB_ADMIN_PORT, share=False)

if __name__ == "__main__":
    panel = WebAdminPanel()
    panel.launch()