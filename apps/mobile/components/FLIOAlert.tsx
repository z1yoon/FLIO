import React, { useState, useEffect, createContext, useContext, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  Modal,
  TouchableOpacity,
  TouchableWithoutFeedback,
  Dimensions,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';

const { width } = Dimensions.get('window');

export type FLIOAlertButton = {
  text: string;
  onPress?: () => void;
  style?: 'default' | 'cancel' | 'destructive';
};

type FLIOAlertProps = {
  visible: boolean;
  title: string;
  message?: string;
  buttons?: FLIOAlertButton[];
  onClose: () => void;
};

function FLIOAlert({
  visible,
  title,
  message,
  buttons = [{ text: '확인', onPress: () => {} }],
  onClose,
}: FLIOAlertProps) {
  const handleButtonPress = (button: FLIOAlertButton) => {
    onClose();
    // Execute button callback after modal is dismissed
    if (button.onPress) {
      setTimeout(() => {
        button.onPress!();
      }, 100);
    }
  };

  return (
    <Modal
      visible={visible}
      transparent
      animationType="fade"
      onRequestClose={onClose}
    >
      <TouchableWithoutFeedback onPress={onClose}>
        <View style={styles.overlay}>
          <TouchableWithoutFeedback>
            <View style={styles.modalContainer}>
              <LinearGradient
                colors={['#2E7D7A', '#4FD1C7']}
                style={styles.modalGradient}
              >
                {/* Title */}
                <Text style={styles.title}>{title}</Text>
                
                {/* Message */}
                {message && (
                  <Text style={styles.message}>{message}</Text>
                )}

                {/* Buttons */}
                <View style={styles.buttonContainer}>
                  {buttons.map((button, index) => {
                    const isCancel = button.style === 'cancel';
                    const isDestructive = button.style === 'destructive';
                    
                    return (
                      <TouchableOpacity
                        key={index}
                        style={[
                          styles.button,
                          buttons.length > 1 && index > 0 && styles.buttonSpacing,
                        ]}
                        onPress={() => handleButtonPress(button)}
                        activeOpacity={0.8}
                      >
                        {isCancel || isDestructive ? (
                          <View style={styles.secondaryButton}>
                            <Text style={[
                              styles.buttonText,
                              isDestructive && styles.destructiveText,
                            ]}>
                              {button.text}
                            </Text>
                          </View>
                        ) : (
                          <LinearGradient
                            colors={['#00FFC8', '#00D4AA']}
                            start={{ x: 0, y: 0 }}
                            end={{ x: 1, y: 0 }}
                            style={styles.primaryButton}
                          >
                            <Text style={styles.primaryButtonText}>
                              {button.text}
                            </Text>
                          </LinearGradient>
                        )}
                      </TouchableOpacity>
                    );
                  })}
                </View>
              </LinearGradient>
            </View>
          </TouchableWithoutFeedback>
        </View>
      </TouchableWithoutFeedback>
    </Modal>
  );
}

// Alert queue to prevent modal-on-modal crashes
interface QueuedAlert {
  title: string;
  message?: string;
  buttons?: FLIOAlertButton[];
}

// Global ref to store the show function - set by provider
let globalShowAlert: ((title: string, message?: string, buttons?: FLIOAlertButton[]) => void) | null = null;

export function FLIOAlertProvider({ children }: { children: React.ReactNode }) {
  const [alertState, setAlertState] = useState<{
    visible: boolean;
    title: string;
    message?: string;
    buttons?: FLIOAlertButton[];
  }>({
    visible: false,
    title: '',
  });

  // Queue to handle multiple alerts
  const queueRef = useRef<QueuedAlert[]>([]);
  const isShowingRef = useRef(false);

  // Use ref to keep show function stable
  const showRef = useRef<(title: string, message?: string, buttons?: FLIOAlertButton[]) => void>();

  // Process the next alert in queue
  const processQueue = () => {
    if (queueRef.current.length > 0 && !isShowingRef.current) {
      const nextAlert = queueRef.current.shift();
      if (nextAlert) {
        isShowingRef.current = true;
        setAlertState({
          visible: true,
          title: nextAlert.title,
          message: nextAlert.message,
          buttons: nextAlert.buttons || [{ text: '확인', onPress: () => {} }],
        });
      }
    }
  };

  showRef.current = (title: string, message?: string, buttons?: FLIOAlertButton[]) => {
    queueRef.current.push({ title, message, buttons });
    processQueue();
  };

  const handleClose = () => {
    isShowingRef.current = false;
    setAlertState({ ...alertState, visible: false });
    // Process next alert after a small delay to allow modal dismiss animation
    setTimeout(() => {
      processQueue();
    }, 300);
  };

  // Set global ref immediately when component mounts
  useEffect(() => {
    globalShowAlert = (title: string, message?: string, buttons?: FLIOAlertButton[]) => {
      if (showRef.current) {
        showRef.current(title, message, buttons);
      }
    };
    return () => {
      globalShowAlert = null;
    };
  }, []);

  return (
    <>
      {children}
      <FLIOAlert
        visible={alertState.visible}
        title={alertState.title}
        message={alertState.message}
        buttons={alertState.buttons}
        onClose={handleClose}
      />
    </>
  );
}

export const FLIOAlertAPI = {
  alert: (title: string, message?: string, buttons?: FLIOAlertButton[]) => {
    if (globalShowAlert) {
      globalShowAlert(title, message, buttons);
    } else {
      console.warn('FLIOAlertProvider not initialized. Make sure FLIOAlertProvider wraps your app in _layout.tsx');
    }
  },
};

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 24,
  },
  modalContainer: {
    width: width - 48,
    maxWidth: 400,
    borderRadius: 20,
    overflow: 'hidden',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 8,
  },
  modalGradient: {
    padding: 24,
    alignItems: 'center',
  },
  title: {
    fontSize: 20,
    fontWeight: '700',
    color: '#FFFFFF',
    marginBottom: 12,
    textAlign: 'center',
  },
  message: {
    fontSize: 16,
    color: 'rgba(255, 255, 255, 0.8)',
    textAlign: 'center',
    lineHeight: 24,
    marginBottom: 24,
  },
  buttonContainer: {
    width: '100%',
    gap: 12,
  },
  button: {
    width: '100%',
  },
  buttonSpacing: {
    marginTop: 0,
  },
  primaryButton: {
    paddingVertical: 16,
    borderRadius: 30,
    alignItems: 'center',
    justifyContent: 'center',
  },
  primaryButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#FFFFFF',
  },
  secondaryButton: {
    paddingVertical: 16,
    borderRadius: 30,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'transparent',
    borderWidth: 2,
    borderColor: 'rgba(255, 255, 255, 0.6)',
  },
  buttonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#FFFFFF',
  },
  destructiveText: {
    color: '#FF6B6B',
  },
});

export default FLIOAlert;
