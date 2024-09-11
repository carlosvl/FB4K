@isTest
class BatchGetEventEntriesTest {
  private static final String RESPONSE_OK = '{"GetEventEntriesResult":"[{\"__type\":\"BikeRegAPIRegistrationDetail:#PioneerReg.EventRegistration\",\"AmountDiscounted\":0.0000,\"AmtPaid\":59.8300,\"Bib\":\"\",\"CategoryName\":\"freebike 25\",\"ConfirmationNumber\":\"pe0pg6pp\",\"CustomQuestions\":[{\"Answer\":\"Womens Medium\",\"CheckBoxSelected\":null,\"Cost\":0.0000,\"DeferredCost\":0,\"IsHidden\":false,\"OriginalCost\":0,\"OverrideCost\":null,\"PlainAnswer\":\"Womens Medium\",\"QuestionAbbreviation\":\"Shirt\",\"QuestionChoiceID\":0,\"QuestionID\":81700}],\"DateEntered\":\"\\/Date(1709074450223-0500)\\/\",\"EID\":11039577,\"EntryFee\":55.0000,\"EntryMethod\":0,\"EventID\":123456,\"GroupHeaderName\":\"\",\"HideOnWhosRegistered\":false,\"IsCheckedIn\":null,\"IsRaceDay\":false,\"LastModified\":\"\\/Date(1709074452990-0500)\\/\",\"Notes\":\"\",\"PromoterTax\":0.0000,\"Quantity\":1,\"RaceID\":\"123456-3\",\"RaceRecID\":783917,\"TransactionType\":0,\"UserInfo\":{\"__type\":\"BikeRegParticipant:#PioneerReg.User\",\"Address1\":\"4141 ABBOTT AVE S\",\"Address2\":\"\",\"City\":\"Minneapolis\",\"Country\":\"USA\",\"Email\":\"amytrigirl@comcast.net\",\"FirstName\":\"Amy\",\"IsMigrated\":false,\"LastName\":\"Bauch\",\"MiddleName\":null,\"OutsideAccountID\":null,\"Phone\":\"(612) 267-6864\",\"State\":\"MN\",\"ZIP\":\"55410\",\"Team\":\"\",\"Age\":null,\"AgeAtYearEnd\":66,\"AgeOnEventDate\":65,\"DOB\":\"\\/Date(-350852400000-0500)\\/\",\"DOBdd\":19,\"DOBmm\":11,\"DOByyyy\":1958,\"EmergencyContactName\":\"Warren Ferber\",\"EmergencyContactPhone\":\"(612) 790-0822\",\"Gender\":\"F\",\"CurrentCyclocrossAge\":67,\"UCIID\":\"\",\"USACCXRank\":0,\"USACLicense\":\"\",\"UniqueLicenseNumber\":\"\"},\"WaiverStatuses\":[{\"Initials\":\"ab\",\"SignDate\":\"\\/Date(1709074452257-0500)\\/\",\"Signed\":true,\"WaiverID\":21510,\"WaiverTitle\":\"freebike Waiver\"}],\"CrossResultsPoints\":null,\"UCIPoints\":0,\"USACCXRank\":0,\"LicenseStatus\":\"n\\/a\",\"RankingPoints\":0}]"}';
  private static final String RESPONSE_EMPTY = '{"GetEventEntriesResult":"[]"}';

  @isTest
  static void testBatchExecute() {
    // Create Config
    BikeRegAPI__mdt config = TestDataFactory.generateBikeRegApiConfig(
      'Defaults',
      'https://www.BikeReg.com/api/director/',
      'user@test.fb4k',
      'pass1234'
    );
    // Create Custom Setting
    BikeRegToken__c cSetting = TestDataFactory.generateBikeRegTokenSetting(
      '1234-1234-token',
      Datetime.now().addDays(1)
    );
    insert cSetting;

    Campaign camp = TestDataFactory.generateCampaign(
      'Test Campaign',
      Date.today(),
      true,
      '123456'
    );
    insert camp;

    HttpResponse res = new HttpResponse();
    res.setBody(RESPONSE_OK);
    res.setStatusCode(200);
    HttpMock mock = new HttpMock();
    mock.addMock(res);
    Test.setMock(HttpCalloutMock.class, mock);

    List<CampaignMember> members = [
      SELECT Id
      FROM CampaignMember
      WHERE CampaignId = :camp.Id
    ];
    System.assertEquals(0, members.size());

    Test.startTest();
    BatchGetEventEntries batch = new BatchGetEventEntries(config);
    Database.executeBatch(batch);
    Test.stopTest();

    members = [SELECT Id FROM CampaignMember WHERE CampaignId = :camp.Id];
    System.assertEquals(1, members.size());
  }

  @isTest
  static void testBatchExecuteEmptyResponse() {
    // Create Config
    BikeRegAPI__mdt config = TestDataFactory.generateBikeRegApiConfig(
      'Defaults',
      'https://www.BikeReg.com/api/director/',
      'user@test.fb4k',
      'pass1234'
    );
    // Create Custom Setting
    BikeRegToken__c cSetting = TestDataFactory.generateBikeRegTokenSetting(
      '1234-1234-token',
      Datetime.now().addDays(1)
    );
    insert cSetting;

    Campaign camp = TestDataFactory.generateCampaign(
      'Test Campaign',
      Date.today(),
      true,
      '123456'
    );
    insert camp;

    HttpResponse res = new HttpResponse();
    res.setBody(RESPONSE_EMPTY);
    res.setStatusCode(200);
    HttpMock mock = new HttpMock();
    mock.addMock(res);
    Test.setMock(HttpCalloutMock.class, mock);

    List<CampaignMember> members = [
      SELECT Id
      FROM CampaignMember
      WHERE CampaignId = :camp.Id
    ];
    System.assertEquals(0, members.size());

    Test.startTest();
    BatchGetEventEntries batch = new BatchGetEventEntries(config);
    Database.executeBatch(batch);
    Test.stopTest();

    members = [SELECT Id FROM CampaignMember WHERE CampaignId = :camp.Id];
    System.assertEquals(0, members.size());
  }

  @isTest
  static void testSchedule() {
    String CRON_EXP =
      '0 0 0 3 9 ? ' +
      String.valueOf(Date.today().year() + 1) +
      '';
    Test.startTest();
    String jobId = System.schedule(
      'BatchGetEventEntriesTest',
      CRON_EXP,
      new BatchGetEventEntries()
    );

    // Get the information from the CronTrigger API object
    CronTrigger ct = [
      SELECT Id, CronExpression, TimesTriggered, NextFireTime
      FROM CronTrigger
      WHERE id = :jobId
    ];

    // Verify the expressions are the same
    System.assertEquals(CRON_EXP, ct.CronExpression);

    // Verify the job has not run
    System.assertEquals(0, ct.TimesTriggered);

    // Verify the next time the job will run
    System.assertEquals(
      String.valueOf(Date.today().year() + 1) + '-09-03 00:00:00',
      String.valueOf(ct.NextFireTime)
    );
    Test.stopTest();
  }
}