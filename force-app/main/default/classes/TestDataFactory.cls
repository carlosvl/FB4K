@isTest
public with sharing class TestDataFactory {
  public static BikeRegAPI__mdt generateBikeRegApiConfig(
    String name,
    String base,
    String username,
    String password
  ) {
    BikeRegAPI__mdt config = new BikeRegAPI__mdt();
    config.DeveloperName = name;
    config.BaseURL__c = String.isNotBlank(base) ? base : '';
    config.Username__c = String.isNotBlank(username) ? username : '';
    config.Password__c = String.isNotBlank(password) ? password : '';
    return config;
  }

  public static BikeRegToken__c generateBikeRegTokenSetting(
    String value,
    Datetime expirationDate
  ) {
    BikeRegToken__c cSetting = new BikeRegToken__c();
    cSetting.Value__c = String.isNotBlank(value) ? value : '';
    cSetting.ExpirationDate__c = expirationDate != null
      ? expirationDate
      : Datetime.now().addDays(1);
    return cSetting;
  }

  public static Campaign generateCampaign(
    String name,
    Date startDate,
    Boolean isActive,
    String externalId
  ) {
    Campaign camp = new Campaign();
    camp.Name = String.isNotBlank(name)
      ? name
      : 'TestCampaign_' + Datetime.now().getTime();
    camp.StartDate = startDate != null ? startDate : Date.today();
    camp.IsActive = isActive != null ? isActive : true;
    camp.Event_External_Id__c = externalId != null
      ? externalId.toUpperCase()
      : '-1';
    return camp;
  }
}