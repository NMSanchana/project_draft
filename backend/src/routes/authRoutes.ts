import { Router } from 'express';
import { registerUser, loginUser, googleAuthUser, updateUserProfile } from '../controllers/authController';

const router = Router();

router.post('/register', registerUser);
router.post('/login', loginUser);
router.post('/google', googleAuthUser);
router.put('/profile', updateUserProfile);

export default router;
