global class BatchGetEventEntries implements Schedulable, Database.Batchable<sObject>, Database.Stateful, Database.AllowsCallouts {
  @TestVisible
  private BikeRegAPI__mdt config;

  public BatchGetEventEntries() {
  }

  public BatchGetEventEntries(BikeRegAPI__mdt apiConfig) {
    this.config = apiConfig;
  }

  global void execute(SchedulableContext sc) {
    BatchGetEventEntries batch = new BatchGetEventEntries();
    Database.executeBatch(this);
  }

  global Database.QueryLocator start(Database.BatchableContext bc) {
    String query = 'SELECT Id, Event_External_Id__c, StartDate FROM Campaign WHERE Event_External_Id__c <> NULL AND IsActive = TRUE AND StartDate <> NULL';
    return Database.getQueryLocator(query);
  }

  global void execute(Database.BatchableContext bc, List<Campaign> scope) {
    if (scope != null && !scope.isEmpty()) {
      for (Campaign campaignRecord : scope) {
        BikeRegAPIInterface.getEventEntries(
          campaignRecord.Event_External_Id__c,
          String.valueOf(campaignRecord.StartDate),
          config
        );
      }
    }
  }

  global void finish(Database.BatchableContext bc) {
  }
}