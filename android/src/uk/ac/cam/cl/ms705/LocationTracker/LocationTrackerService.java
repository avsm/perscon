package uk.ac.cam.cl.ms705.LocationTracker;

import java.io.ByteArrayOutputStream;
import java.io.PrintWriter;
import java.io.StringWriter;
import java.util.ArrayList;
import java.util.List;
import java.util.StringTokenizer;
import java.util.Timer;
import java.util.TimerTask;

import org.apache.http.HttpResponse;
import org.apache.http.NameValuePair;
import org.apache.http.auth.AuthenticationException;
import org.apache.http.client.entity.UrlEncodedFormEntity;
import org.apache.http.client.methods.HttpGet;
import org.apache.http.client.methods.HttpPost;
import org.apache.http.entity.StringEntity;
import org.apache.http.impl.client.DefaultHttpClient;
import org.apache.http.message.BasicNameValuePair;
import org.apache.http.protocol.HTTP;
import org.json.JSONStringer;

import android.app.Notification;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.location.Criteria;
import android.location.Location;
import android.location.LocationManager;
import android.net.Uri;
import android.os.IBinder;
import android.util.Log;


public class LocationTrackerService extends Service {


   // **********************************************
   // static data/shared references, etc.
   // **********************************************
   public static ServiceUpdateUIListener UI_UPDATE_LISTENER;
   private static LocationTracker MAIN_ACTIVITY;
   
   private String GOOGLE_USERNAME;
   private String GOOGLE_PW; 

   // **********************************************
   // data
   // **********************************************
   private Timer timer = new Timer();
   private static final long UPDATE_INTERVAL = 120000;
   DefaultHttpClient httpclient = new DefaultHttpClient();
   
   
   private NotificationManager mNotificationManager;
   private int LOCATIONTRACKER_NOTIFICATION_ID; 
   
   // **********************************************
   // hooks into other activities
   // **********************************************
   public static void setMainActivity(LocationTracker activity) {
     MAIN_ACTIVITY = activity;
   }

   public static void setUpdateListener(ServiceUpdateUIListener l) {
     UI_UPDATE_LISTENER = l;
   }

   // **********************************************
   // lifecycle methods
   // **********************************************

   /** not using ipc... dont care about this method */
   public IBinder onBind(Intent intent) {
     return null;
   }

   @Override 
   public void onCreate() {
     super.onCreate();

     // set up Google login
     this.GOOGLE_USERNAME = MAIN_ACTIVITY.getGoogleUsername();
     this.GOOGLE_PW = MAIN_ACTIVITY.getGooglePasswd();
     
     
     // init the service here
     _startService();
     

     if (MAIN_ACTIVITY != null) AppUtils.showToastShort(MAIN_ACTIVITY, "LocationTrackerService started");
   }

   @Override 
   public void onDestroy() {
     super.onDestroy();

     _shutdownService();

     if (MAIN_ACTIVITY != null) AppUtils.showToastShort(MAIN_ACTIVITY, "LocationTrackerService stopped");
   }

   // **************************************************
   // service business logic
   // **************************************************
   private void _startService() {
     timer.scheduleAtFixedRate(
         new TimerTask() {
           public void run() {
             _getLocationUpdate();
           }
         },
         0,
         UPDATE_INTERVAL);
     Log.i(getClass().getSimpleName(), "Timer started!!!");
     
     // Set up notification
     // Get the notification manager service.
     mNotificationManager = (NotificationManager) getSystemService(NOTIFICATION_SERVICE);
    
     _showNotification(R.drawable.icon, R.string.notif_short, R.string.notif_detailed, false);
    
   }

   private void _showNotification(int statusBarIconID, int statusBarTextID, int detailedTextID, boolean showIconOnly) {
      
      // choose the ticker text
      String tickerText = showIconOnly ? null : this.getString(statusBarTextID);
   
      Notification notif = new Notification(
            statusBarIconID,             // the icon for the status bar
            tickerText,                  // the text to display in the ticker
            System.currentTimeMillis()  // the timestamp for the notification
            );
            
      Context context = getApplicationContext();
      CharSequence contentTitle = this.getString(statusBarTextID);
      CharSequence contentText = this.getString(detailedTextID);
      Intent notificationIntent = new Intent(this, LocationTracker.class);
      PendingIntent contentIntent = PendingIntent.getActivity(this, 0, notificationIntent, 0);

      notif.setLatestEventInfo(context, contentTitle, contentText, contentIntent);

      notif.flags |= Notification.FLAG_ONGOING_EVENT;
      
      mNotificationManager.notify(
            LOCATIONTRACKER_NOTIFICATION_ID,   // we use a string id because it is a unique
                                               // number.  we use it later to cancel the
                                               // notification
            notif);
   
   }
   
   
   private void _clearNotification() {
      mNotificationManager.cancel(LOCATIONTRACKER_NOTIFICATION_ID);
   }
   
   
   /** dont forget to fire update to the ui listener */
   private void _getLocationUpdate() {
     Log.i(getClass().getSimpleName(), "background task - start");

     try {
        
        LocationManager lm = (LocationManager)getSystemService(Context.LOCATION_SERVICE);
        Criteria loccrit = new Criteria();
        loccrit.setAccuracy(Criteria.ACCURACY_FINE);
        loccrit.setAccuracy(Criteria.POWER_HIGH);
        String provider = lm.getBestProvider(loccrit, true);
        if(provider == null) 
           Log.e(getClass().getSimpleName(), "failed to get location provider");
        
        // Get the location
        Location loc = lm.getLastKnownLocation(provider);
        
        // Log the location
        Log.i(getClass().getSimpleName(), loc.toString());
        
        // Make HTTP post
        _postLocationData(loc);
        
     }
     catch (Exception e) {
       StringWriter sw = new StringWriter();
       PrintWriter pw = new PrintWriter(sw);
       e.printStackTrace(pw);
       Log.e(getClass().getSimpleName(), sw.getBuffer().toString(), e);
     }

     Log.i(getClass().getSimpleName(), "background task - end");

     if (UI_UPDATE_LISTENER != null) {
       //UI_UPDATE_LISTENER.updateUI(DataFromServlet);
     }
   }
   
   
   private boolean _GAEAuthenticate(String username, String password) {
      Log.d(getClass().getSimpleName(), "Num cookies before login: " + httpclient.getCookieStore().getCookies().size());

      // Set up google.com login request parameters
      List <NameValuePair> nvps = new ArrayList<NameValuePair>();
      nvps.add(new BasicNameValuePair("Email", username));
      nvps.add(new BasicNameValuePair("Passwd", password));
      nvps.add(new BasicNameValuePair("service", "ah"));
      nvps.add(new BasicNameValuePair("source", "personalcloud")); // used by google for accounting
      nvps.add(new BasicNameValuePair("accountType", "GOOGLE"));  //using HOSTED here will do bad things for hosted accounts

      // Login at Google.com
      try {
         HttpPost httpost = new HttpPost("https://www.google.com/accounts/ClientLogin");
         httpost.setEntity(new UrlEncodedFormEntity(nvps, HTTP.UTF_8));
         HttpResponse response = httpclient.execute(httpost);
         Log.i(getClass().getSimpleName(), "Google.com Login Response: " + response.getStatusLine());
   
         // Find authkey in response body to pass to Appspot.com
         ByteArrayOutputStream ostream = new ByteArrayOutputStream();
         response.getEntity().writeTo(ostream);
         String strResponse = ostream.toString();
         Log.v(getClass().getSimpleName(), strResponse);
         StringTokenizer st = new StringTokenizer(strResponse, "\n\r=");
         String authKey = null;
         while(st.hasMoreTokens()) {
            if(st.nextToken().equalsIgnoreCase("auth")) {
               authKey = st.nextToken();
               Log.d(getClass().getSimpleName(), "AUTH = " + authKey);
               break;
            }
         }
   
         // Do a GET with authkey to get cookie from Appspot.com
         HttpGet httpget = new HttpGet("https://ms705-cl.appspot.com/_ah/login?auth=" + authKey + "&continue=" + "http%3A//ms705-cl.appspot.com/loc");
         response = httpclient.execute(httpget);
         Log.i(getClass().getSimpleName(), "Appspot.com Login Response: " + response.getStatusLine());
         Log.d(getClass().getSimpleName(), "Num cookies after login: " + httpclient.getCookieStore().getCookies().size());
         
      } catch (Exception e) {
         Log.e(getClass().getSimpleName(), "failed to log in to google.com");
         StringWriter sw = new StringWriter();
         PrintWriter pw = new PrintWriter(sw);
         e.printStackTrace(pw);
         Log.e(getClass().getSimpleName(), sw.getBuffer().toString(), e);
      }
      
      return (httpclient.getCookieStore().getCookies().size() > 0);
      //return true;
   }
   
   
   private void _postLocationData(Location loc) {
      // Preparing the post operation 
      try {
         
         // Check if we are authenticated with GAE and do so if now
         if (!_GAEAuthenticate(this.GOOGLE_USERNAME, this.GOOGLE_PW)) {
            Log.e(getClass().getSimpleName(), "Failed to authenticate to GAE!");
            throw new AuthenticationException();
         }
         
         HttpPost httpost = new HttpPost("https://ms705-cl.appspot.com/update/android");
         
         String jsonStr = new JSONStringer()
            .object()
               .key("lat").value(loc.getLatitude())
               .key("lon").value(loc.getLongitude())
               .key("accuracy").value(loc.getAccuracy())
               .key("date").value(loc.getTime() / 1000)
            .endObject()
            .toString();
         
         Log.i(getClass().getSimpleName(), "JSON: " + jsonStr);
         httpost.setEntity(new StringEntity(jsonStr));
         
         // Post, check and show the result (not really spectacular, but works):
         HttpResponse response = httpclient.execute(httpost);
         Log.i(getClass().getSimpleName(), "POST response: " + response.getStatusLine());
         ByteArrayOutputStream ostream = new ByteArrayOutputStream();
         while (response.getEntity().isStreaming()) {
            response.getEntity().writeTo(ostream);
         }
         Log.e(getClass().getSimpleName(), ostream.toString());
      } catch (Exception e) {
         Log.e(getClass().getSimpleName(), "failed to make POST request");
         StringWriter sw = new StringWriter();
         PrintWriter pw = new PrintWriter(sw);
         e.printStackTrace(pw);
         Log.e(getClass().getSimpleName(), sw.getBuffer().toString(), e);
      }
      
   }

   private void _shutdownService() {
     if (timer != null) timer.cancel();
     _clearNotification();
     Log.i(getClass().getSimpleName(), "Timer stopped!!!");
   }

}
