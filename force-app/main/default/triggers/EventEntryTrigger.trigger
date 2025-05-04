trigger EventEntryTrigger on EventEntry__e(after insert) {
  if (Trigger.isAfter) {
    if (Trigger.isInsert) {
      EventEntryTriggerHandler.handleAfterInsert(Trigger.new);
    }
  }
}