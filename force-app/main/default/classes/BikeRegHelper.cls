public with sharing class BikeRegHelper {
  public static void parseEventEntries(String eventId, String res) {
    EventEntryWrapper wrapper = EventEntryWrapper.parse(res);
    List<EventEntry__e> entries = new List<EventEntry__e>();
    if (wrapper != null) {
      for (
        EventEntryWrapper.GetEventEntriesResult entry : wrapper.GetEventEntriesResult
      ) {
        EventEntry__e e = new EventEntry__e();
        e.EventId__c = eventId;
        e.Body__c = JSON.serialize(entry);
        entries.add(e);
      }
      List<Database.SaveResult> results = EventBus.publish(entries);
    }
  }
}