confirmButton.onclick=async()=>{
 if(!canConfirmSnapshot(lastStatus))return;
 const snapshot=reviewSnapshot,epoch=reviewEpoch;
 const confirmation={schema:'fx3-review-snapshot-v1',request_id:crypto.randomUUID().toLowerCase()};
 for(const k of reviewIdentityKeys)confirmation[k]=snapshot[k];
 pendingConfirm=confirmation;reviewAwaiting=true;disableKeys();pinButton.disabled=true;
 try{
  const ack=await post('/api/confirm-visual',confirmation);
  if(!reviewAsyncCurrent(epoch,snapshot.attempt_id,snapshot.step))return;
  if(ack.confirmed!==true||ack.schema!=='fx3-review-snapshot-v1'||ack.request_id!==confirmation.request_id||
     ack.guest_input_written!==false||reviewIdentityKeys.some(k=>ack[k]!==confirmation[k]))throw Error('snapshot_confirm_receipt_mismatch');
  if(pendingConfirm===confirmation){
   reviewLastAck=Object.freeze({...ack});reviewAwaiting=false;reviewUnknown=false;pendingConfirm=null;
   reviewLabel.textContent='已确认该固定副本；下一键仍需新的明确动作并通过实时输入门。';
   if(explicitRejection?.kind==='confirm')explicitRejection=null;
  }
 }catch(e){
  if(epoch===reviewEpoch){reviewUnknown=true;uncertainDetail='指定快照确认结果未知；请结束本轮，不会重发。';invalidateReview('confirm_unknown',true);}
 }finally{if(lastStatus)enableKeys(lastStatus);}
};
