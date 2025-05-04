public with sharing class EventEntryTriggerHandler {
  public static void handleAfterInsert(List<EventEntry__e> newEventEntries) {
    Set<String> entriesEmail = new Set<String>();
    Set<String> eventIds = new Set<String>();
    Map<String, EventEntryWrapper.UserInfo> emailEntriesMap = new Map<String, EventEntryWrapper.UserInfo>();
    for (EventEntry__e entry : newEventEntries) {
      EventEntryWrapper.GetEventEntriesResult entryWrap = (EventEntryWrapper.GetEventEntriesResult) JSON.deserialize(
        entry.Body__c,
        EventEntryWrapper.GetEventEntriesResult.class
      );

      entriesEmail.add(entryWrap.UserInfo.Email);
      emailEntriesMap.put(entryWrap.UserInfo.Email, entryWrap.UserInfo);
      eventIds.add(String.valueOf(entryWrap.EventID));
    }
    if (
      entriesEmail != null &&
      !entriesEmail.isEmpty() &&
      emailEntriesMap != null &&
      !emailEntriesMap.isEmpty() &&
      eventIds != null &&
      !eventIds.isEmpty()
    ) {
      handleEntries(entriesEmail, emailEntriesMap, eventIds);
    }
  }

  private static void handleEntries(
    Set<String> entriesEmail,
    Map<String, EventEntryWrapper.UserInfo> emailEntriesMap,
    Set<String> eventIds
  ) {
    List<Contact> finalContacts = new List<Contact>();
    Map<String, Contact> contactsMap = getContacts(entriesEmail);

    if (contactsMap == null || contactsMap.isEmpty()) {
      for (String email : emailEntriesMap.keySet()) {
        Contact ctc = new Contact();
        ctc = fillContactData(ctc, emailEntriesMap.get(email), false);
        finalContacts.add(ctc);
      }
    } else {
      for (String email : emailEntriesMap.keySet()) {
        Contact ctc;
        Boolean isUpdate = false;
        if (contactsMap.containsKey(email)) {
          ctc = contactsMap.get(email);
          isUpdate = true;
        } else {
          ctc = new Contact();
        }
        ctc = fillContactData(ctc, emailEntriesMap.get(email), isUpdate);
        finalContacts.add(ctc);
      }
    }
    handleContactsAndCampaignMembers(finalContacts, eventIds);
  }

  private static Map<String, Contact> getContacts(Set<String> contactsEmail) {
    Map<String, Contact> contactsMap = new Map<String, Contact>();
    List<Contact> contactsList = [
      SELECT Id, Email
      FROM Contact
      WHERE Email IN :contactsEmail
      ORDER BY LastModifiedDate
    ];
    if (contactsList != null && !contactsList.isEmpty()) {
      for (Contact c : contactsList) {
        contactsMap.put(c.Email, c);
      }
    }
    return contactsMap;
  }

  private static Map<String, Campaign> getCampaigns(Set<String> eventIds) {
    Map<String, Campaign> campaignMap = new Map<String, Campaign>();
    List<Campaign> campList = [
      SELECT Id, Event_External_Id__c
      FROM Campaign
      WHERE Event_External_Id__c IN :eventIds
    ];
    if (campList != null && !campList.isEmpty()) {
      for (Campaign c : campList) {
        campaignMap.put(c.Event_External_Id__c, c);
      }
    }
    return campaignMap;
  }

  private static void handleContactsAndCampaignMembers(
    List<Contact> finalContacts,
    Set<String> eventIds
  ) {
    if (finalContacts != null && !finalContacts.isEmpty()) {
      upsert finalContacts;
      Map<String, Campaign> campaignMap = getCampaigns(eventIds);
      if (campaignMap != null && !campaignMap.isEmpty()) {
        List<CampaignMember> campMembers = new List<CampaignMember>();
        for (Contact ctc : finalContacts) {
          for (Campaign camp : campaignMap.values()) {
            CampaignMember campMember = new CampaignMember();
            campMember.CampaignId = camp.Id;
            campMember.ContactId = ctc.Id;
            campMembers.add(campMember);
          }
        }
        if (campMembers != null && !campMembers.isEmpty()) {
          upsert campMembers;
        }
      }
    }
  }

  private static Contact fillContactData(
    Contact ctc,
    EventEntryWrapper.UserInfo userInfo,
    Boolean isUpdate
  ) {
    if (!isUpdate) {
      ctc.FirstName = userInfo.FirstName;
      ctc.LastName = userInfo.LastName;
      ctc.Email = userInfo.Email;
    }
    ctc.Phone = userInfo.Phone;
    ctc.MailingStreet = userInfo.Address1;
    ctc.MailingCity = userInfo.City;
    ctc.MailingState = userInfo.State;
    ctc.MailingPostalCode = userInfo.ZIP;
    ctc.OtherStreet = String.isNotBlank(userInfo.Address2)
      ? userInfo.Address2
      : '';
    ctc.Gender__c = String.isBlank(userInfo.Gender)
      ? ''
      : userInfo.Gender.equals('M')
          ? 'Male'
          : userInfo.Gender.equals('F') ? 'Female' : 'Other';
    ctc.Birthdate = Date.newInstance(
      userInfo.DOByyyy,
      userInfo.DOBmm,
      userInfo.DOBdd
    );
    return ctc;
  }
}