from zlapi.models import Message, MultiMsgStyle, MessageStyle
from config import PREFIX, ADMIN
ADMIN_ID = ADMIN



import time

def handle_span_command(message, message_object, thread_id, thread_type, author_id, client):
    if author_id not in ADMIN:
        msg = "• Bạn không có quyền sử dụng lệnh này."
        client.replyMessage(Message(text=msg), message_object, thread_id, thread_type, ttl=12000)
        return

    if not message_object.quote:
        return

    msg2undo = message_object.quote
    msg_id = msg2undo.globalMsgId
    cli_msg_id = msg2undo.cliMsgId
    msg2del = message_object.quote
    action = "/-heart"
    
    try:
        while True:
            client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
            client.deleteGroupMsg(msg2del.globalMsgId, msg2del.ownerId, msg2del.cliMsgId, thread_id)
            client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)            
            client.deleteGroupMsg(msg2del.globalMsgId, msg2del.ownerId, msg2del.cliMsgId, thread_id)            
            client.undoMessage(msg_id, cli_msg_id, thread_id, thread_type)
            client.deleteGroupMsg(msg2del.globalMsgId, msg2del.ownerId, msg2del.cliMsgId, thread_id)            
            client.undoMessage(msg_id, cli_msg_id, thread_id, thread_type)            
            client.deleteGroupMsg(msg2del.globalMsgId, msg2del.ownerId, msg2del.cliMsgId, thread_id)            
            client.undoMessage(msg_id, cli_msg_id, thread_id, thread_type)            
            client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
            client.undoMessage(msg_id, cli_msg_id, thread_id, thread_type)
                        
    except Exception as e:
        print(f'Error: {e}')
    

def get_mitaizl():
    return {
        'spam.hiden': handle_span_command
    }