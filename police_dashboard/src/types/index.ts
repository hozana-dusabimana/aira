export type UserRole = 'citizen' | 'officer' | 'admin';

export type IncidentStatus =
  | 'pending'
  | 'analyzing'
  | 'verified'
  | 'assigned'
  | 'in_progress'
  | 'resolved'
  | 'rejected';

export type SeverityLevel = 'low' | 'medium' | 'high' | 'critical';

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user_id: number;
  role: UserRole;
}

export interface User {
  id: number;
  full_name: string;
  email: string;
  phone?: string;
  role: UserRole;
  is_verified: boolean;
  is_active: boolean;
  created_at: string;
}

export interface Officer {
  id: number;
  user_id: number;
  badge_number: string;
  station_id?: number;
  rank?: string;
  department?: string;
  created_at: string;
}

export interface Station {
  id: number;
  name: string;
  district?: string;
  sector?: string;
  latitude?: number;
  longitude?: number;
  contact_phone?: string;
}

export interface IncidentImage {
  id: number;
  image_url: string;
  image_order: number;
}

export interface AIAnalysis {
  id: number;
  detected_objects?: Array<{ label: string; confidence: number }>;
  scene_label?: string;
  caption?: string;
  confidence_score?: number;
  model_version?: string;
  created_at: string;
}

export interface IncidentReporter {
  id: number;
  full_name: string;
  phone?: string;
}

export interface Incident {
  id: number;
  reporter_id: number;
  reporter?: IncidentReporter;
  image_url?: string;
  ai_description?: string;
  user_description?: string;
  incident_type?: string;
  severity_level: SeverityLevel;
  latitude?: number;
  longitude?: number;
  status: IncidentStatus;
  assigned_officer_id?: number;
  station_id?: number;
  created_at: string;
  updated_at: string;
  resolved_at?: string;
  images?: IncidentImage[];
  ai_analysis?: AIAnalysis;
}

export interface OverviewMetrics {
  total_reports: number;
  pending: number;
  resolved: number;
  in_progress: number;
  average_response_minutes: number | null;
}

export interface CountByLabel {
  label: string;
  count: number;
}

export interface TimelinePoint {
  date: string;
  count: number;
}

export interface IncidentMessage {
  id: number;
  incident_id: number;
  sender_id: number;
  sender_role: string;
  message: string;
  created_at: string;
}

export interface Notification {
  id: number;
  title: string;
  message?: string;
  type: string;
  related_incident_id?: number;
  is_read: boolean;
  created_at: string;
}

export interface SpamReport {
  id: number;
  incident_id?: number;
  reporter_id?: number;
  reporter?: IncidentReporter;
  image_url?: string;
  incident_type?: string;
  reason?: string;
  duplicate_of_incident_id?: number;
  ai_caption?: string;
  ai_description?: string;
  user_description?: string;
  latitude?: number;
  longitude?: number;
  created_at: string;
}
