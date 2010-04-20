package uk.ac.cam.cl.ms705.LocationTracker;

import android.app.Activity;
import android.content.Intent;
import android.os.Bundle;
import android.util.Log;
import android.view.View;
import android.view.View.OnClickListener;
import android.widget.Button;
import android.widget.EditText;

public class LocationTracker extends Activity {

   private Intent svc;
   
   private Button startButton;
   
   private OnClickListener startListener;
   private OnClickListener stopListener; 
   
   /** Called when the activity is first created. */
   @Override
   public void onCreate(Bundle icicle) {
      super.onCreate(icicle);
      try {
         // setup and start Location Tracker Service
         
         svc =  new Intent(this, LocationTrackerService.class);
         
         LocationTrackerService.setMainActivity(this);
           
         startListener = new OnClickListener() {
            public void onClick(View v) {
               _start();
            }
         };
         
         stopListener = new OnClickListener() {
            public void onClick(View v) {
               _stop();
            }
         };
         
         // Set up UI
         setContentView(R.layout.main);
         startButton = (Button)findViewById(R.id.StartStopTrackingButton);
         startButton.setOnClickListener(startListener);
      }
      catch (Exception e) {
         Log.e(getClass().getSimpleName(), "ui creation problem", e);
      }

    }

    @Override protected void onDestroy() {
      super.onDestroy();

      // stop Location Tracker Service
      {
        stopService(svc);
      }

    }
    
    
    public String getGoogleUsername() {
       
       EditText field = (EditText)findViewById(R.id.googleUsername); 
       
       return field.getText().toString();
       
    }
    
    
    public String getGooglePasswd() {
       
       EditText field = (EditText)findViewById(R.id.googlePwd); 
       
       return field.getText().toString();
       
    }
    
    
    private void _stop() {
       stopService(svc);
       startButton.setText(R.string.start_button_label);
       startButton.setOnClickListener(startListener);
    }
    
    
    private void _start() {
       startService(svc);
       startButton.setText(R.string.stop_button_label);
       startButton.setOnClickListener(stopListener);
    }
}